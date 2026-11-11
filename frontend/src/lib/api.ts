import "server-only";
import { cookies, headers } from "next/headers";
import { resolvePublicApiUrl } from "./public-url";

// URL de la API vista desde el servidor de Next.js (red interna de Docker).
// El navegador nunca llama a la API directamente (salvo el widget público).
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

/** URL pública de la API (widget.js). null en producción si no hay una URL pública válida. */
export function publicApiUrl() {
  // Se lee en cada petición: la variable de Render llega en tiempo de ejecución.
  return resolvePublicApiUrl({
    API_PUBLIC_URL: process.env.API_PUBLIC_URL,
    API_INTERNAL_URL: process.env.API_INTERNAL_URL,
    NODE_ENV: process.env.NODE_ENV,
  });
}

/** Cookie con el negocio elegido en el panel. Solo SELECCIONA: Django decide si el usuario pertenece. */
export const BUSINESS_COOKIE = "negocio";

export type ApiError = {
  code: string;
  message: string;
  fields?: Record<string, string[]>;
};

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; error: ApiError };

const UNAVAILABLE: ApiError = {
  code: "unavailable",
  message: "El servicio no está disponible. Inténtalo más tarde.",
};

const TIMEOUT: ApiError = {
  code: "timeout",
  message: "El servidor tardó demasiado en responder.",
};

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; token?: string } = {},
): Promise<ApiResult<T>> {
  const requestHeaders: Record<string, string> = {};
  if (options.body !== undefined) requestHeaders["Content-Type"] = "application/json";
  if (options.token) {
    requestHeaders["Authorization"] = `Token ${options.token}`;
    const business = (await cookies()).get(BUSINESS_COOKIE)?.value;
    if (business && /^\d+$/.test(business)) requestHeaders["X-Business-Id"] = business;
  }
  // Los rate limits de la API se aplican por IP del visitante, no del servidor web.
  const forwardedFor = (await headers()).get("x-forwarded-for");
  if (forwardedFor) requestHeaders["X-Forwarded-For"] = forwardedFor;

  try {
    const response = await fetch(`${API_INTERNAL_URL}${path}`, {
      method: options.method ?? "GET",
      headers: requestHeaders,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: AbortSignal.timeout(8000),
    });
    const data = response.status === 204 ? null : await response.json();
    if (response.ok) return { ok: true, status: response.status, data: data as T };
    return { ok: false, status: response.status, error: data?.error ?? UNAVAILABLE };
  } catch (error) {
    // AbortSignal.timeout lanza TimeoutError: se distingue de una API caída.
    if (error instanceof Error && error.name === "TimeoutError") {
      return { ok: false, status: 504, error: TIMEOUT };
    }
    return { ok: false, status: 503, error: UNAVAILABLE };
  }
}

export type CheckState = "ok" | "error";

export type Health = {
  backend: CheckState;
  database: CheckState;
  chatbot: CheckState;
};

type HealthBody = { checks?: { database?: string; chatbot?: string } };

export async function getHealth(): Promise<Health> {
  try {
    const response = await fetch(`${API_INTERNAL_URL}/api/health/`, {
      signal: AbortSignal.timeout(5000),
    });
    // La API responde 200 o 503 con el mismo cuerpo JSON.
    const body: HealthBody = await response.json();
    return {
      backend: "ok",
      database: body.checks?.database === "ok" ? "ok" : "error",
      chatbot: body.checks?.chatbot === "ok" ? "ok" : "error",
    };
  } catch {
    return { backend: "error", database: "error", chatbot: "error" };
  }
}
