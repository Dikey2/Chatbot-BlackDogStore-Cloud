import "server-only";
import { cookies } from "next/headers";
import { api, type ApiError } from "./api";

const COOKIE_NAME = "session";
const DEFAULT_MAX_AGE_SECONDS = 60 * 60 * 8;
const EXPIRED_LOGIN_PATH = "/login?motivo=expirada";

export type User = { id: number; name: string; email: string; role: string };

export async function getToken(): Promise<string | undefined> {
  return (await cookies()).get(COOKIE_NAME)?.value;
}

// El token vive en una cookie httpOnly: el JavaScript del navegador no puede leerlo.
// La cookie caduca a la vez que el token de la API (expires_at).
export async function saveToken(token: string, expiresAt?: string) {
  const secondsLeft = expiresAt
    ? Math.floor((Date.parse(expiresAt) - Date.now()) / 1000)
    : DEFAULT_MAX_AGE_SECONDS;
  (await cookies()).set(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.COOKIE_SECURE === "true",
    path: "/",
    maxAge: Math.max(0, Number.isFinite(secondsLeft) ? secondsLeft : DEFAULT_MAX_AGE_SECONDS),
  });
}

export async function clearToken() {
  (await cookies()).delete(COOKIE_NAME);
}

export type Session =
  | { state: "authenticated"; user: User; token: string }
  | { state: "anonymous"; expired: boolean }
  | { state: "unavailable"; reason: "timeout" | "unavailable" };

/** Ruta de login; con aviso si la API indicó que la sesión expiró. */
export function loginPath(error?: ApiError | null) {
  return error?.code === "token_expired" ? EXPIRED_LOGIN_PATH : "/login";
}

/**
 * Estado de la sesión. Distingue "sin sesión" (token ausente o rechazado) de
 * "API no disponible", para no mandar al login a quien tiene sesión válida.
 */
export async function getSession(): Promise<Session> {
  const token = await getToken();
  if (!token) return { state: "anonymous", expired: false };
  const result = await api<User>("/api/users/me/", { token });
  if (result.ok) return { state: "authenticated", user: result.data, token };
  if (result.status !== 401) {
    return { state: "unavailable", reason: result.error.code === "timeout" ? "timeout" : "unavailable" };
  }
  return { state: "anonymous", expired: result.error.code === "token_expired" };
}
