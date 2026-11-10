import { NextResponse, type NextRequest } from "next/server";
import { isLocale } from "@/lib/i18n";
import { LOCALE_COOKIE } from "@/lib/locale";

/** La preferencia de idioma no modifica la sesión ni el contenido de la base de datos. */
export async function POST(request: NextRequest) {
  const form = await request.formData();
  const chosen = form.get("lang");
  if (!isLocale(chosen)) return new NextResponse("Unsupported locale", { status: 400 });

  // Volver a la página actual, solo si el Referer es de este mismo sitio (evita
  // redirecciones a dominios externos). Se compara con el Host que ve el navegador:
  // detrás de Docker o de Render, request.url lleva la dirección interna del servidor.
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const referer = request.headers.get("referer");
  let destination = "/";
  try {
    const source = referer ? new URL(referer) : null;
    if (source && source.host === host) destination = source.pathname + source.search;
  } catch {
    // Referer mal formado: se vuelve al inicio.
  }

  // Location relativa: el navegador la resuelve contra la dirección que está usando.
  const response = new NextResponse(null, { status: 303, headers: { Location: destination } });
  response.cookies.set(LOCALE_COOKIE, chosen, {
    path: "/",
    sameSite: "lax",
    httpOnly: true,
    secure: process.env.COOKIE_SECURE === "true",
    maxAge: 60 * 60 * 24 * 365,
  });
  return response;
}
