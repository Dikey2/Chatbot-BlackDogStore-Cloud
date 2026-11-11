/**
 * URL pública de la API: la que el NAVEGADOR de un visitante usa para cargar
 * widget.js (código de instalación y vista previa del panel).
 *
 * Se resuelve EN TIEMPO DE EJECUCIÓN (no en el build): Next.js solo incrusta en el
 * build las variables NEXT_PUBLIC_*, y estas páginas se generan en cada petición.
 *
 * Orden:
 * 1. API_PUBLIC_URL, si es una URL http(s) que un navegador puede abrir. Si el
 *    operador escribió localhost a propósito (stack local), se respeta.
 * 2. API_INTERNAL_URL, si es una URL https pública (en Render ya es el backend público).
 * 3. Solo en desarrollo: http://localhost:8000.
 * En producción nunca se CAE en localhost por falta de configuración, y nunca se usa
 * un nombre interno de Docker ("backend"): sin URL válida se devuelve null y el panel
 * muestra un aviso en vez de un código roto.
 *
 * Sin dependencias de Next: se prueba con el ejecutor de pruebas de Node.
 */
export type PublicUrlEnv = {
  API_PUBLIC_URL?: string;
  API_INTERNAL_URL?: string;
  NODE_ENV?: string;
};

export type PublicUrl = {
  url: string | null;
  source: "API_PUBLIC_URL" | "API_INTERNAL_URL" | "desarrollo" | null;
  problem: string | null;
};

const DEV_FALLBACK = "http://localhost:8000";

function parse(value: string | undefined): URL | null {
  const text = (value ?? "").trim();
  if (!text) return null;
  try {
    const url = new URL(text);
    return url.protocol === "http:" || url.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

/** Nombre interno de Docker ("backend", "db"): ningún navegador puede resolverlo. */
export function isInternalHost(hostname: string): boolean {
  const host = hostname.toLowerCase();
  return host !== "localhost" && !host.includes(".") && !host.includes(":") && !host.startsWith("[");
}

/** localhost, IPs de loopback o nombres internos de Docker. */
export function isPrivateHost(hostname: string): boolean {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, "");
  return (
    host === "localhost" ||
    host.endsWith(".localhost") ||
    host === "0.0.0.0" ||
    host === "::1" ||
    host.startsWith("127.") ||
    !host.includes(".")
  );
}

function clean(url: URL): string {
  return `${url.protocol}//${url.host}${url.pathname}`.replace(/\/+$/, "");
}

export function resolvePublicApiUrl(env: PublicUrlEnv): PublicUrl {
  const production = env.NODE_ENV === "production";
  const explicit = parse(env.API_PUBLIC_URL);
  if (explicit && !isInternalHost(explicit.hostname)) {
    return { url: clean(explicit), source: "API_PUBLIC_URL", problem: null };
  }
  const internal = parse(env.API_INTERNAL_URL);
  if (internal && internal.protocol === "https:" && !isPrivateHost(internal.hostname)) {
    return { url: clean(internal), source: "API_INTERNAL_URL", problem: null };
  }
  if (!production) {
    return { url: DEV_FALLBACK, source: "desarrollo", problem: null };
  }
  return {
    url: null,
    source: null,
    problem: explicit
      ? "API_PUBLIC_URL apunta a un nombre interno de Docker; los navegadores no pueden usarlo."
      : "Falta configurar API_PUBLIC_URL (URL https pública del backend) en el servicio del frontend.",
  };
}
