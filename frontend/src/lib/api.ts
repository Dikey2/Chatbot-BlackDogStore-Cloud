import "server-only";
import { headers } from "next/headers";

// URL de la API vista desde el servidor de Next.js (red interna de Docker).
// El navegador nunca llama a la API directamente.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

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

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; token?: string } = {},
): Promise<ApiResult<T>> {
  const requestHeaders: Record<string, string> = {};
  if (options.body !== undefined) requestHeaders["Content-Type"] = "application/json";
  if (options.token) requestHeaders["Authorization"] = `Token ${options.token}`;
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
  } catch {
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
