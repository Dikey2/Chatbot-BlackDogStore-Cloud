// Regresión: el código de instalación y la vista previa del widget nunca deben
// usar localhost ni un nombre interno de Docker en producción.
// Ejecutar: npm run test:unit
import assert from "node:assert/strict";
import { test } from "node:test";
import { isInternalHost, isPrivateHost, resolvePublicApiUrl } from "../src/lib/public-url.ts";

const RENDER_BACKEND = "https://chatbot-blackdogstore-cloud.onrender.com";

test("usa API_PUBLIC_URL cuando está configurada (sin barra final)", () => {
  const r = resolvePublicApiUrl({ NODE_ENV: "production", API_PUBLIC_URL: `${RENDER_BACKEND}/` });
  assert.deepEqual(r, { url: RENDER_BACKEND, source: "API_PUBLIC_URL", problem: null });
});

test("sin API_PUBLIC_URL, en Render usa API_INTERNAL_URL https pública", () => {
  const r = resolvePublicApiUrl({ NODE_ENV: "production", API_INTERNAL_URL: RENDER_BACKEND });
  assert.equal(r.url, RENDER_BACKEND);
  assert.equal(r.source, "API_INTERNAL_URL");
});

test("en producción nunca devuelve localhost (caso del incidente)", () => {
  const r = resolvePublicApiUrl({ NODE_ENV: "production" });
  assert.equal(r.url, null);
  assert.match(r.problem, /API_PUBLIC_URL/);
});

test("en producción rechaza un nombre interno de Docker en API_PUBLIC_URL", () => {
  const r = resolvePublicApiUrl({ NODE_ENV: "production", API_PUBLIC_URL: "http://backend:8000" });
  assert.equal(r.url, null);
  assert.match(r.problem, /interno/);
});

test("localhost escrito a propósito (stack local en modo producción) se respeta", () => {
  const r = resolvePublicApiUrl({ NODE_ENV: "production", API_PUBLIC_URL: "http://localhost:8010" });
  assert.equal(r.url, "http://localhost:8010");
});

test("en producción no usa el nombre interno de Docker de API_INTERNAL_URL", () => {
  const r = resolvePublicApiUrl({ NODE_ENV: "production", API_INTERNAL_URL: "http://backend:8000" });
  assert.equal(r.url, null);
});

test("valores mal escritos no producen una URL", () => {
  const r = resolvePublicApiUrl({ NODE_ENV: "production", API_PUBLIC_URL: "chatbot.onrender.com" });
  assert.equal(r.url, null);
});

test("en desarrollo local el respaldo sigue siendo localhost:8000", () => {
  assert.equal(resolvePublicApiUrl({ NODE_ENV: "development" }).url, "http://localhost:8000");
  assert.equal(
    resolvePublicApiUrl({ NODE_ENV: "development", API_PUBLIC_URL: "http://localhost:8010" }).url,
    "http://localhost:8010",
  );
});

test("detecta nombres internos de Docker", () => {
  for (const host of ["backend", "db", "chatbot"]) assert.ok(isInternalHost(host), host);
  for (const host of ["localhost", "127.0.0.1", "chatbot-blackdogstore-cloud.onrender.com"]) assert.ok(!isInternalHost(host), host);
});

test("detecta hosts privados", () => {
  for (const host of ["localhost", "127.0.0.1", "backend", "::1", "app.localhost"]) assert.ok(isPrivateHost(host), host);
  assert.ok(!isPrivateHost("chatbot-blackdogstore-cloud.onrender.com"));
});
