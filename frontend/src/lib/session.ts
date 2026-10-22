import "server-only";
import { cookies } from "next/headers";
import { api } from "./api";

const COOKIE_NAME = "session";
const MAX_AGE_SECONDS = 60 * 60 * 8;

export type User = { id: number; name: string; email: string; role: string };

export async function getToken(): Promise<string | undefined> {
  return (await cookies()).get(COOKIE_NAME)?.value;
}

// El token vive en una cookie httpOnly: el JavaScript del navegador no puede leerlo.
export async function saveToken(token: string) {
  (await cookies()).set(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.COOKIE_SECURE === "true",
    path: "/",
    maxAge: MAX_AGE_SECONDS,
  });
}

export async function clearToken() {
  (await cookies()).delete(COOKIE_NAME);
}

export type Session =
  | { state: "authenticated"; user: User; token: string }
  | { state: "anonymous" }
  | { state: "unavailable" };

/**
 * Estado de la sesión. Distingue "sin sesión" (token ausente o rechazado) de
 * "API no disponible", para no mandar al login a quien tiene sesión válida.
 */
export async function getSession(): Promise<Session> {
  const token = await getToken();
  if (!token) return { state: "anonymous" };
  const result = await api<User>("/api/users/me/", { token });
  if (result.ok) return { state: "authenticated", user: result.data, token };
  return result.status === 401 ? { state: "anonymous" } : { state: "unavailable" };
}
