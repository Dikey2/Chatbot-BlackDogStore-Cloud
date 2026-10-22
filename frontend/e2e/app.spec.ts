import { chromium, expect, test, type Page } from "@playwright/test";

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

  test("el chat sin sesión redirige al login", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login$/);
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

  test("otro usuario no ve el historial del primero", async ({ page }) => {
    await page.goto("/registro");
    await fillAndSubmit(
      page,
      {
        Nombre: "Otra Persona E2E",
        Correo: `e2e-otro-${Date.now()}@example.com`,
        "Contraseña (mínimo 8 caracteres)": PASSWORD,
      },
      "Registrarme",
    );
    await expect(page).toHaveURL(/\/chat$/);
    await expect(page.getByTestId("session-user")).toHaveText("Otra Persona E2E (cliente)");
    await expect(page.getByText("Escribe tu consulta para comenzar.")).toBeVisible();
    await expect(chatMessages(page)).toHaveCount(0);
    for (const text of expectedHistory) {
      await expect(page.getByText(text, { exact: true })).toHaveCount(0);
    }
    expect(expectedHistory).toHaveLength(6);
  });
});
