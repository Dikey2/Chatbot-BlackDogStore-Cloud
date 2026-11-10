"use server";

import { refresh } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { api, BUSINESS_COOKIE, type ApiError } from "@/lib/api";
import { clearToken, getToken, loginPath } from "@/lib/session";

/** Estado común de los formularios del panel. */
export type PanelFormState = {
  message?: string;
  fields?: Record<string, string[]>;
  saved?: boolean;
  sentAt?: number;
};

export type ActionResult = { ok: true } | { ok: false; message: string };

async function requireToken() {
  const token = await getToken();
  if (!token) redirect("/login");
  return token;
}

// Las acciones solo reenvían a la API: el permiso lo comprueba Django en cada petición.
async function call<T>(path: string, method: string, body?: unknown) {
  const token = await requireToken();
  const result = await api<T>(path, { method, token, body });
  if (!result.ok && result.status === 401) {
    await clearToken();
    redirect(loginPath(result.error));
  }
  return result;
}

/** Aplana los errores anidados de DRF (p. ej. chatbot.primary_color) a "campo: mensaje". */
function flatten(error: ApiError): PanelFormState {
  const fields: Record<string, string[]> = {};
  const walk = (value: unknown, prefix: string) => {
    if (Array.isArray(value)) fields[prefix] = value.map(String);
    else if (value && typeof value === "object")
      for (const [key, inner] of Object.entries(value)) walk(inner, prefix ? `${prefix}.${key}` : key);
  };
  walk(error.fields ?? {}, "");
  return { message: error.message, fields };
}

const text = (form: FormData, name: string) => String(form.get(name) ?? "").trim();

// ---------------------------------------------------------------- selección de negocio

export async function selectBusinessAction(form: FormData) {
  const id = text(form, "business");
  const store = await cookies();
  if (/^\d+$/.test(id)) {
    store.set(BUSINESS_COOKIE, id, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.COOKIE_SECURE === "true",
      path: "/",
      maxAge: 60 * 60 * 24 * 30,
    });
  } else {
    store.delete(BUSINESS_COOKIE);
  }
  const next = text(form, "next");
  redirect(next.startsWith("/") && !next.startsWith("//") ? next : "/panel");
}

// ---------------------------------------------------------------- negocio actual

export async function updateBusinessAction(_: PanelFormState, form: FormData): Promise<PanelFormState> {
  const body = {
    name: text(form, "name"),
    description: text(form, "description"),
    logo_url: text(form, "logo_url"),
    chatbot: {
      assistant_name: text(form, "assistant_name"),
      welcome_message: text(form, "welcome_message"),
      no_answer_message: text(form, "no_answer_message"),
      handoff_message: text(form, "handoff_message"),
      handoff_keywords: text(form, "handoff_keywords"),
      schedule: text(form, "schedule"),
      contact_info: text(form, "contact_info"),
      primary_color: text(form, "primary_color"),
      is_active: form.get("is_active") === "on",
    },
  };
  const result = await call("/api/business/", "PATCH", body);
  if (!result.ok) return flatten(result.error);
  refresh();
  return { saved: true, sentAt: Date.now() };
}

export async function addDomainAction(_: PanelFormState, form: FormData): Promise<PanelFormState> {
  const result = await call("/api/business/domains/", "POST", { origin: text(form, "origin") });
  if (!result.ok) return flatten(result.error);
  refresh();
  return { saved: true, sentAt: Date.now() };
}

export async function deleteDomainAction(id: number): Promise<ActionResult> {
  const result = await call(`/api/business/domains/${id}/`, "DELETE");
  if (!result.ok) return { ok: false, message: result.error.message };
  refresh();
  return { ok: true };
}

export async function addMemberAction(_: PanelFormState, form: FormData): Promise<PanelFormState> {
  const result = await call("/api/business/members/", "POST", {
    email: text(form, "email"),
    name: text(form, "name"),
    password: String(form.get("password") ?? ""),
    role: text(form, "role") || "asesor",
  });
  if (!result.ok) return flatten(result.error);
  refresh();
  return { saved: true, sentAt: Date.now() };
}

export async function removeMemberAction(id: number): Promise<ActionResult> {
  const result = await call(`/api/business/members/${id}/`, "DELETE");
  if (!result.ok) {
    const fields = result.error.fields as Record<string, string[]> | undefined;
    return { ok: false, message: fields?.role?.[0] ?? result.error.message };
  }
  refresh();
  return { ok: true };
}

// ---------------------------------------------------------------- plataforma

export async function createBusinessAction(_: PanelFormState, form: FormData): Promise<PanelFormState> {
  const result = await call("/api/platform/businesses/", "POST", {
    name: text(form, "name"),
    slug: text(form, "slug"),
    description: text(form, "description"),
  });
  if (!result.ok) return flatten(result.error);
  refresh();
  return { saved: true, sentAt: Date.now() };
}

export async function updatePlatformBusinessAction(
  id: number,
  _: PanelFormState,
  form: FormData,
): Promise<PanelFormState> {
  const result = await call(`/api/platform/businesses/${id}/`, "PATCH", {
    name: text(form, "name"),
    description: text(form, "description"),
  });
  if (!result.ok) return flatten(result.error);
  refresh();
  return { saved: true, sentAt: Date.now() };
}

export async function setBusinessStateAction(id: number, active: boolean): Promise<ActionResult> {
  const result = await call(`/api/platform/businesses/${id}/${active ? "activate" : "suspend"}/`, "POST");
  if (!result.ok) return { ok: false, message: result.error.message };
  refresh();
  return { ok: true };
}

export async function addBusinessAdminAction(
  id: number,
  _: PanelFormState,
  form: FormData,
): Promise<PanelFormState> {
  const result = await call(`/api/platform/businesses/${id}/admins/`, "POST", {
    email: text(form, "email"),
    name: text(form, "name"),
    password: String(form.get("password") ?? ""),
  });
  if (!result.ok) return flatten(result.error);
  refresh();
  return { saved: true, sentAt: Date.now() };
}

// ---------------------------------------------------------------- bandeja

export async function takeConversationAction(id: number): Promise<ActionResult> {
  const result = await call(`/api/chat/conversations/${id}/take/`, "POST");
  if (!result.ok) return { ok: false, message: result.error.message };
  refresh();
  return { ok: true };
}
