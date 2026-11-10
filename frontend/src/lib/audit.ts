import "server-only";
import { api, type ApiResult } from "./api";

export const AUDIT_ACTIONS = [
  "registro",
  "login",
  "login_fallido",
  "logout",
  "token_expirado",
  "acceso_denegado",
  "faq_crear",
  "faq_editar",
  "faq_eliminar",
  "conversacion_responder",
  "conversacion_cerrar",
  "conversacion_derivar",
  "conversacion_asignar",
  "negocio_crear",
  "negocio_editar",
  "negocio_suspender",
  "negocio_activar",
  "chatbot_configurar",
  "dominio_agregar",
  "dominio_eliminar",
  "miembro_agregar",
  "miembro_eliminar",
] as const;
export type AuditAction = (typeof AUDIT_ACTIONS)[number];
export const AUDIT_RESULTS = ["exito", "fallo"] as const;
export type AuditResult = (typeof AUDIT_RESULTS)[number];

export type AuditEvent = {
  id: number;
  user: number | null;
  user_name: string | null;
  email: string;
  action: AuditAction;
  result: AuditResult;
  source: string;
  detail: string;
  created_at: string;
  business?: number | null;
  business_name?: string | null;
};

export type AuditPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditEvent[];
};

export function listAudit(
  token: string,
  filters: { action?: AuditAction; result?: AuditResult; page: number },
): Promise<ApiResult<AuditPage>> {
  const query = new URLSearchParams({ page: String(filters.page) });
  if (filters.action) query.set("action", filters.action);
  if (filters.result) query.set("result", filters.result);
  return api<AuditPage>(`/api/audit/?${query}`, { token });
}

/** Auditoría de toda la plataforma (superadministrador). scope "plataforma" = eventos sin negocio. */
export function listPlatformAudit(
  token: string,
  filters: { scope: "todos" | "plataforma"; page: number },
): Promise<ApiResult<AuditPage>> {
  const query = new URLSearchParams({ page: String(filters.page) });
  if (filters.scope === "plataforma") query.set("business", "none");
  return api<AuditPage>(`/api/platform/audit/?${query}`, { token });
}
