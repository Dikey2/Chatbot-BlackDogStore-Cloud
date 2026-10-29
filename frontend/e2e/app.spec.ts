import { chromium, expect, test, type Locator, type Page } from "@playwright/test";

// Datos ficticios, únicos por ejecución.
const PASSWORD = "Clave-ficticia-123";
const EMAIL = `e2e-${Date.now()}@example.com`;
const NAME = "Persona E2E";

async function fillAndSubmit(page: Page, values: Record<string, string>, button: string) {
  for (const [label, value] of Object.entries(values)) {
    await page.getByLabel(label).fill(value);
  }
  await page.getByRole("button", { name: button }).click();
}

test.describe("páginas públicas", () => {
  test("el inicio muestra los tres servicios operativos", async ({ page }) => {
    await page.goto("/");
    for (const id of ["status-backend", "status-database", "status-chatbot"]) {
      await expect(page.getByTestId(id)).toHaveText("Operativo");
    }
  });

  test("una ruta inexistente responde 404 con la página propia", async ({ page }) => {
    const response = await page.goto("/no-existe");
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "404: página no encontrada" })).toBeVisible();
  });

  test("páginas de mantenimiento y en desarrollo", async ({ page }) => {
    await page.goto("/mantenimiento");
    await expect(page.getByRole("heading", { name: "Sitio en mantenimiento" })).toBeVisible();
    await page.goto("/en-desarrollo");
    await expect(page.getByRole("heading", { name: "Sección en desarrollo" })).toBeVisible();
  });

  test("el chat y la administración sin sesión redirigen al login", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login$/);
    await page.goto("/admin/faqs");
    await expect(page).toHaveURL(/\/login$/);
    await page.goto("/admin/auditoria");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("el selector de idioma cambia la interfaz y se mantiene al recargar", async ({ page }) => {
    await page.goto("/mantenimiento");
    await page.getByRole("button", { name: "EN" }).click();
    await expect(page.getByRole("heading", { name: "Site under maintenance" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: "Site under maintenance" })).toBeVisible();
    await page.getByRole("button", { name: "ES" }).click();
    await expect(page.getByRole("heading", { name: "Sitio en mantenimiento" })).toBeVisible();
  });
});

const HORARIO = "¿Cuál es el horario de atención?";
const PRECIO = "¿Cuánto cuesta la laptop X?";
const OTRA = "¿Tienen garantía?";

function chatMessages(page: Page) {
  return page.getByTestId("messages").locator("li.message");
}

async function sendMessage(page: Page, text: string) {
  const before = await chatMessages(page).count();
  await page.getByLabel("Mensaje").fill(text);
  await page.getByRole("button", { name: "Enviar" }).click();
  await expect(chatMessages(page)).toHaveCount(before + 2);
}

/** Textos visibles del chat, en el orden en que se muestran. */
async function visibleHistory(page: Page) {
  return chatMessages(page).allTextContents();
}

// Las pruebas de este bloque dependen unas de otras y comparten el usuario EMAIL.
// En total hacen 7 peticiones de autenticación (límite: 10 por minuto e IP).
test.describe.serial("registro, chat, historial y sesión", () => {
  let expectedHistory: string[] = [];

  test("registro, chat, recarga, reapertura del navegador y cierre de sesión", async ({
    page,
    context,
  }) => {
    await page.goto("/registro");
    await fillAndSubmit(
      page,
      { Nombre: NAME, Correo: EMAIL, "Contraseña (mínimo 8 caracteres)": PASSWORD },
      "Registrarme",
    );
    await expect(page).toHaveURL(/\/chat$/);
    await expect(page.getByTestId("session-user")).toHaveText(`${NAME} (cliente)`);
    await expect(chatMessages(page)).toHaveCount(0);

    // El token queda en una cookie que el JavaScript de la página no puede leer.
    const session = (await context.cookies()).find((cookie) => cookie.name === "session");
    expect(session?.httpOnly).toBe(true);
    expect(await page.evaluate(() => document.cookie)).not.toContain("session");

    await sendMessage(page, HORARIO);
    await expect(chatMessages(page).nth(0)).toHaveText(HORARIO);
    await expect(chatMessages(page).nth(1)).toContainText("DATO FICTICIO: atendemos de lunes a sábado");
    await expect(page.getByTestId("escalated")).toHaveCount(0);

    await sendMessage(page, PRECIO);
    await expect(chatMessages(page).nth(3)).toContainText("La derivaré a un asesor");
    await expect(page.getByTestId("escalated")).toBeVisible();
    expectedHistory = await visibleHistory(page);
    expect(expectedHistory).toHaveLength(4);

    // Recarga (Command + R): el historial vuelve desde PostgreSQL, en el mismo orden.
    await page.reload();
    await expect(chatMessages(page)).toHaveCount(4);
    expect(await visibleHistory(page)).toEqual(expectedHistory);
    await expect(page.getByTestId("escalated")).toBeVisible();

    // Cerrar el navegador y abrir otro con las cookies guardadas, como hace un navegador real.
    const storageState = await context.storageState();
    const reopened = await chromium.launch();
    try {
      const reopenedContext = await reopened.newContext({
        storageState,
        baseURL: "http://localhost:3000",
      });
      const reopenedPage = await reopenedContext.newPage();
      await reopenedPage.goto("/chat");
      await expect(reopenedPage.getByTestId("session-user")).toHaveText(`${NAME} (cliente)`);
      await expect(chatMessages(reopenedPage)).toHaveCount(4);
      expect(await visibleHistory(reopenedPage)).toEqual(expectedHistory);
    } finally {
      await reopened.close();
    }

    // Un cliente que escribe a mano rutas de administración ve "acceso restringido",
    // también después de recargar: lo decide el servidor en cada petición.
    for (const path of ["/admin/auditoria", "/admin/faqs", "/asesor"]) {
      await page.goto(path);
      await expect(visible(page.getByTestId("role-forbidden"))).toBeVisible();
    }
    await page.reload();
    await expect(visible(page.getByTestId("role-forbidden"))).toBeVisible();
    await page.goto("/chat");

    await page.getByRole("button", { name: "Cerrar sesión" }).click();
    await expect(page).toHaveURL(/\/$/);
    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("el registro rechaza un correo ya usado", async ({ page }) => {
    await page.goto("/registro");
    await fillAndSubmit(
      page,
      { Nombre: NAME, Correo: EMAIL, "Contraseña (mínimo 8 caracteres)": PASSWORD },
      "Registrarme",
    );
    await expect(page.getByText("Ya existe una cuenta con este correo.")).toBeVisible();
    await expect(page).toHaveURL(/\/registro$/);
    await expect(page.getByLabel("Correo")).toHaveValue(EMAIL);
  });

  test("al volver a iniciar sesión se recupera el historial y la conversación continúa", async ({
    page,
  }) => {
    await page.goto("/login");
    await fillAndSubmit(page, { Correo: EMAIL, Contraseña: "incorrecta-999" }, "Entrar");
    await expect(page.getByTestId("form-error")).toHaveText("Correo o contraseña incorrectos.");
    await expect(page).toHaveURL(/\/login$/);

    await fillAndSubmit(page, { Correo: EMAIL, Contraseña: PASSWORD }, "Entrar");
    await expect(page).toHaveURL(/\/chat$/);
    await expect(page.getByTestId("session-user")).toContainText(NAME);
    await expect(chatMessages(page)).toHaveCount(4);
    expect(await visibleHistory(page)).toEqual(expectedHistory);

    // El mensaje nuevo se agrega a la misma conversación, después de los anteriores.
    await sendMessage(page, OTRA);
    await page.reload();
    await expect(chatMessages(page)).toHaveCount(6);
    const history = await visibleHistory(page);
    expect(history.slice(0, 4)).toEqual(expectedHistory);
    expect(history[4]).toBe(OTRA);
    expect(history[5]).toContain("12 meses de garantía");
    expectedHistory = history;
  });

  test("otro usuario no ve el historial; su consulta derivada la atiende un asesor", async ({
    page,
    browser,
  }) => {
    const otherName = `Otra Persona ${Date.now()}`;
    await page.goto("/registro");
    await fillAndSubmit(
      page,
      {
        Nombre: otherName,
        Correo: `e2e-otro-${Date.now()}@example.com`,
        "Contraseña (mínimo 8 caracteres)": PASSWORD,
      },
      "Registrarme",
    );
    await expect(page).toHaveURL(/\/chat$/);
    await expect(page.getByTestId("session-user")).toHaveText(`${otherName} (cliente)`);
    await expect(page.getByText("Escribe tu consulta para comenzar.")).toBeVisible();
    await expect(chatMessages(page)).toHaveCount(0);
    for (const text of expectedHistory) {
      await expect(page.getByText(text, { exact: true })).toHaveCount(0);
    }
    expect(expectedHistory).toHaveLength(6);

    // Un cliente no puede administrar FAQ ni entrar a la bandeja del asesor.
    await page.goto("/admin/faqs");
    await expect(page.getByTestId("role-forbidden")).toBeVisible();
    await expect(page.getByTestId("faq-table")).toHaveCount(0);
    await page.goto("/asesor");
    await expect(page.getByTestId("role-forbidden")).toBeVisible();

    // Consulta sin respuesta: queda derivada.
    await page.goto("/chat");
    await sendMessage(page, PRECIO);
    await expect(page.getByTestId("escalated")).toBeVisible();

    test.skip(!process.env.DEMO_PASSWORD, "Definir DEMO_PASSWORD para probar la bandeja del asesor.");

    // El asesor la atiende desde otro navegador.
    const advisorContext = await browser.newContext();
    try {
      const advisor = await advisorContext.newPage();
      await advisor.goto("/login");
      await fillAndSubmit(
        advisor,
        { Correo: "asesor@example.com", Contraseña: process.env.DEMO_PASSWORD! },
        "Entrar",
      );
      await expect(advisor).toHaveURL(/\/chat$/);
      await advisor.getByRole("link", { name: "Bandeja del asesor" }).click();
      await expect(advisor).toHaveURL(/\/asesor$/);
      const row = visible(advisor.getByRole("row", { name: new RegExp(otherName) }));
      await expect(row).toHaveCount(1);
      await row.getByRole("link", { name: "Ver conversación" }).click();

      const advisorMessages = visible(advisor.getByTestId("messages")).locator("li.message");
      await expect(advisorMessages).toHaveCount(2);
      await expect(advisorMessages.nth(0)).toContainText(PRECIO);
      await expect(visible(advisor.getByTestId("conversation-status"))).toHaveText("derivada");

      const reply = "DATO FICTICIO: un asesor confirmará el precio por correo.";
      await visible(advisor.getByLabel("Respuesta al cliente")).fill(reply);
      await visible(advisor.getByRole("button", { name: "Responder" })).click();
      await expect(visible(advisor.getByText("Respuesta enviada."))).toBeVisible();
      await expect(advisorMessages).toHaveCount(3);
      await expect(advisorMessages.nth(2)).toContainText(reply);
      await expect(visible(advisor.getByLabel("Respuesta al cliente"))).toHaveValue("");

      // El cliente ve la respuesta del asesor al recargar.
      await page.reload();
      await expect(chatMessages(page)).toHaveCount(3);
      await expect(chatMessages(page).nth(2)).toHaveAttribute("data-sender", "asesor");
      await expect(chatMessages(page).nth(2)).toContainText(reply);

      // El asesor no administra FAQ.
      const conversationUrl = advisor.url();
      await advisor.goto("/admin/faqs");
      await expect(advisor.getByTestId("role-forbidden")).toBeVisible();

      // Cierre de la conversación.
      await advisor.goto(conversationUrl);
      advisor.once("dialog", (dialog) => dialog.accept());
      await advisor.getByRole("button", { name: "Cerrar conversación" }).click();
      await expect(advisor.getByTestId("conversation-status")).toHaveText("cerrada");
      await expect(advisor.getByTestId("conversation-closed")).toBeVisible();
      await expect(advisor.getByLabel("Respuesta al cliente")).toHaveCount(0);
    } finally {
      await advisorContext.close();
    }

    // El cliente ve el cierre; su siguiente mensaje empieza otra conversación.
    await page.reload();
    await expect(page.getByTestId("conversation-closed")).toBeVisible();
    await expect(chatMessages(page)).toHaveCount(3);
    await page.getByLabel("Mensaje").fill(OTRA);
    await page.getByRole("button", { name: "Enviar" }).click();
    await expect(chatMessages(page)).toHaveCount(2);
    await expect(page.getByTestId("conversation-closed")).toHaveCount(0);
    await page.reload();
    await expect(chatMessages(page)).toHaveCount(2);
    await expect(chatMessages(page).nth(0)).toHaveText(OTRA);
  });
});

// Requiere DEMO_PASSWORD (la de seed_demo):  DEMO_PASSWORD=... npm run test:e2e
// Next.js conserva oculta en el DOM la página anterior tras navegar con un enlace
// (React Activity). Las búsquedas se limitan a lo que el usuario ve.
function visible(locator: Locator) {
  return locator.filter({ visible: true });
}

test.describe("administración de preguntas frecuentes", () => {
  test.skip(!process.env.DEMO_PASSWORD, "Definir DEMO_PASSWORD para probar el panel de administrador.");

  test("el administrador crea, edita, desactiva y elimina una FAQ que usa el chatbot", async ({
    page,
  }) => {
    const stamp = Date.now();
    const keyword = `e2eclave${stamp}`;
    const question = `¿Pregunta E2E ${stamp}?`;
    const answer = `DATO FICTICIO E2E ${stamp}.`;
    const edited = `DATO FICTICIO E2E editado ${stamp}.`;
    const row = () =>
      visible(page.getByRole("row", { name: new RegExp(question.replace(/[?¿]/g, ".")) }));

    async function ask(expected: string | RegExp) {
      await page.goto("/chat");
      await sendMessage(page, `consulta ${keyword}`);
      await expect(chatMessages(page).last()).toHaveText(expected);
    }

    await page.goto("/login");
    await fillAndSubmit(
      page,
      { Correo: "admin@example.com", Contraseña: process.env.DEMO_PASSWORD! },
      "Entrar",
    );
    await expect(page).toHaveURL(/\/chat$/);
    await page.getByRole("link", { name: "Administrar FAQ" }).click();
    await expect(page).toHaveURL(/\/admin\/faqs$/);
    await expect(page.getByTestId("faq-table")).toBeVisible();

    // Validación: la API rechaza palabras clave vacías y el formulario conserva lo escrito.
    await visible(page.getByLabel("Categoría")).fill("e2e");
    await visible(page.getByLabel("Pregunta")).fill(question);
    await visible(page.getByLabel("Respuesta")).fill(answer);
    await visible(page.getByLabel("Palabras clave (separadas por coma)")).fill(" , ");
    await page.getByRole("button", { name: "Crear" }).click();
    await expect(page.getByText("Indique al menos una palabra clave.")).toBeVisible();
    await expect(visible(page.getByLabel("Pregunta"))).toHaveValue(question);

    // Crear
    await visible(page.getByLabel("Palabras clave (separadas por coma)")).fill(keyword);
    await page.getByRole("button", { name: "Crear" }).click();
    await expect(page.getByText("Pregunta frecuente creada.")).toBeVisible();
    await expect(visible(page.getByLabel("Pregunta"))).toHaveValue("");
    await expect(row()).toContainText("Activa");
    await ask(answer);

    // Editar
    await page.goto("/admin/faqs");
    await row().getByRole("link", { name: "Editar" }).click();
    await expect(visible(page.getByLabel("Respuesta"))).toHaveValue(answer);
    await visible(page.getByLabel("Respuesta")).fill(edited);
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page).toHaveURL(/\/admin\/faqs$/);
    await ask(edited);

    // Desactivar: el chatbot deja de usarla y deriva la consulta.
    await page.goto("/admin/faqs");
    await row().getByRole("button", { name: "Desactivar" }).click();
    await expect(row()).toContainText("Inactiva");
    await ask(/La derivaré a un asesor/);

    // Activar de nuevo y eliminar (con confirmación).
    await page.goto("/admin/faqs");
    await row().getByRole("button", { name: "Activar" }).click();
    await expect(row()).toContainText("Activa");
    page.once("dialog", (dialog) => dialog.accept());
    await row().getByRole("button", { name: "Eliminar" }).click();
    await expect(row()).toHaveCount(0);

    // Editar una FAQ inexistente muestra la página 404.
    await page.goto("/admin/faqs/999999");
    await expect(page.getByRole("heading", { name: "404: página no encontrada" })).toBeVisible();

    // Supervisión (misma sesión: no suma inicios de sesión al límite de 10 por minuto).
    await page.goto("/admin/auditoria");
    const table = visible(page.getByTestId("audit-table"));
    await expect(table).toBeVisible();
    // El evento más reciente es la eliminación de la FAQ de esta prueba.
    await expect(table.locator("tbody tr").first()).toHaveAttribute("data-action", "faq_eliminar");
    await expect(table.locator("tbody tr").first()).toContainText("admin@example.com");

    await visible(page.getByLabel("Acción")).selectOption("faq_crear");
    await visible(page.getByRole("button", { name: "Filtrar" })).click();
    await expect(page).toHaveURL(/accion=faq_crear/);
    const rows = visible(page.getByTestId("audit-table")).locator("tbody tr");
    await expect(rows.first()).toHaveAttribute("data-action", "faq_crear");
    const actions = await rows.evaluateAll((all) => all.map((r) => r.getAttribute("data-action")));
    expect(new Set(actions)).toEqual(new Set(["faq_crear"]));
  });
});
