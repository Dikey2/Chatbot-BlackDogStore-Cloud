import { expect, test, type Page } from "@playwright/test";

// Plataforma multiempresa: panel, plataforma y widget en dos webs independientes.
// Requiere `seed_demo` con SEED_PILOT_PUBLIC_ID=bd_demo_blackdog y
// SEED_SECOND_PUBLIC_ID=bd_demo_cafe, y la web del café (`--profile demo`).
// 4 inicios de sesión: ejecutar separado de app.spec.ts si el límite de 10/min se alcanza.
const PASSWORD = process.env.DEMO_PASSWORD ?? "";
const CAFE_URL = process.env.E2E_CAFE_URL ?? "http://localhost:8090";
const PILOT_ID = "bd_demo_blackdog";

test.skip(!PASSWORD, "Definir DEMO_PASSWORD para las pruebas de la plataforma.");

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Correo").fill(email);
  await page.getByLabel("Contraseña").fill(PASSWORD);
  await page.locator("main").getByRole("button", { name: "Entrar" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

function widget(page: Page) {
  const host = page.locator("[data-bd-chatbot]");
  return {
    host,
    launcher: host.locator(".launcher"),
    input: host.locator("textarea"),
    botMessages: host.locator(".msg.bot"),
    human: host.locator(".human"),
  };
}

async function ask(page: Page, text: string) {
  const w = widget(page);
  const before = await w.botMessages.count();
  await w.input.fill(text);
  await w.input.press("Enter");
  await expect(w.botMessages).toHaveCount(before + 1, { timeout: 15000 });
  return w.botMessages.last();
}

test.describe.configure({ mode: "serial" });

test("admin del negocio: métricas, configuración, dominios y código de instalación", async ({ page }) => {
  await login(page, "admin@example.com");
  await page.goto("/panel");
  await expect(page.getByTestId("current-business")).toContainText("Black Dog Store");
  await expect(page.getByTestId("metrics").locator("li")).toHaveCount(6);

  await page.goto("/admin/chatbot");
  await expect(page.getByTestId("install-snippet")).toContainText(`data-chatbot-id="${PILOT_ID}"`);
  await expect(page.getByTestId("install-snippet")).toContainText("/widget.js");

  const origin = `https://e2e-${Date.now()}.example.com`;
  await page.getByTestId("domain-form").getByLabel(/Origen/).fill(origin);
  await page.getByTestId("domain-form").getByRole("button").click();
  await expect(page.getByTestId("domain-list")).toContainText(origin);
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByTestId("domain-list").locator("li", { hasText: origin }).getByRole("button", { name: "Quitar" }).click();
  await expect(page.getByTestId("domain-list")).not.toContainText(origin);

  // Configuración inválida: el servidor la rechaza y el formulario lo muestra.
  const form = page.getByTestId("config-form");
  await form.getByLabel("Logotipo (URL https)").fill("http://inseguro.example.com/logo.png");
  await form.getByRole("button", { name: "Guardar" }).click();
  await expect(form.getByRole("alert").first()).toBeVisible();
});

test("aislamiento: el admin del café no ve datos del piloto ni su panel", async ({ page }) => {
  await login(page, "admin@cafe.example.com");
  await page.goto("/admin/faqs");
  const table = page.getByTestId("faq-table");
  await expect(table).toContainText("carta");
  await expect(table).not.toContainText("garantía");
  await page.goto("/plataforma");
  await expect(page.getByTestId("role-forbidden")).toBeVisible();
});

test("superadministrador: negocios, suspensión y reactivación", async ({ page }) => {
  await login(page, "plataforma@example.com");
  await page.goto("/plataforma");
  await expect(page.getByTestId("business-row-black-dog-store")).toBeVisible();
  const cafe = page.getByTestId("business-row-cafe-aurora");
  await expect(cafe).toContainText("Activo");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByTestId("state-cafe-aurora").click();
  await expect(cafe).toContainText("Suspendido");
  await page.getByTestId("state-cafe-aurora").click();
  await expect(cafe).toContainText("Activo");
  await page.goto("/plataforma/auditoria");
  await expect(page.getByTestId("platform-audit-table")).toContainText("Negocio suspendido");
});

test("widget en la web del café: responde con SUS datos y no duplica el script", async ({ page }) => {
  await page.goto(CAFE_URL);
  const w = widget(page);
  await expect(w.host).toHaveCount(1); // el script se incluye dos veces
  await w.launcher.click();
  await expect(await ask(page, "¿Tienen wifi?")).toContainText("wifi gratuito");
  // La garantía es una FAQ del piloto: aquí no existe y se deriva.
  await expect(await ask(page, "¿Tienen garantía?")).toContainText("asesor");
  await page.keyboard.press("Escape");
  await expect(w.launcher).toHaveAttribute("aria-expanded", "false");
});

test("widget del piloto: el visitante pide asesor y la consulta llega a la bandeja", async ({ page, browser }) => {
  await page.goto(`/vista-previa?id=${PILOT_ID}`);
  const w = widget(page);
  await w.launcher.click();
  const marker = `consulta-e2e-${Date.now()}`;
  // Pregunta con FAQ (no se deriva sola) y luego el visitante pide un asesor.
  await expect(await ask(page, `¿Tienen garantía? ${marker}`)).toContainText("garantía");
  await expect(w.human).toBeEnabled();
  await w.human.click();
  await expect(w.human).toHaveText("Un asesor revisará tu consulta");

  const advisor = await browser.newPage();
  await login(advisor, "asesor@example.com");
  await advisor.goto("/asesor?estado=derivada");
  const row = advisor.getByTestId("inbox-table").locator("tbody tr").first();
  await expect(row).toContainText("Widget");
  await row.getByRole("link", { name: "Ver conversación" }).click();
  await expect(advisor.getByTestId("messages")).toContainText(marker);
  await advisor.getByLabel("Respuesta al cliente").fill("Hola, soy el asesor de prueba");
  await advisor.getByRole("button", { name: "Responder" }).click();
  await expect(advisor.getByText("Respuesta enviada.")).toBeVisible();

  // El widget recibe la respuesta del asesor sin recargar (sondeo cada 5 s).
  await expect(w.host.locator(".msg.asesor")).toContainText("Hola, soy el asesor de prueba", { timeout: 15000 });
});
