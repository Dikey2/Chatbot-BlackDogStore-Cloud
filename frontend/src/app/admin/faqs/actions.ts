"use server";

import { refresh } from "next/cache";
import { redirect } from "next/navigation";
import { api, type ApiError } from "@/lib/api";
import type { Faq } from "@/lib/faqs";
import { clearToken, getToken, loginPath } from "@/lib/session";

export type FaqFormState = {
  message?: string;
  fields?: Record<string, string[]>;
  values?: Record<string, string>;
  saved?: boolean;
};

export type RowActionResult = { ok: true } | { ok: false; message: string };

async function requireToken() {
  const token = await getToken();
  if (!token) redirect("/login");
  return token;
}

function readForm(form: FormData) {
  return {
    category: String(form.get("category") ?? "").trim(),
    question: String(form.get("question") ?? "").trim(),
    answer: String(form.get("answer") ?? "").trim(),
    keywords: String(form.get("keywords") ?? "").trim(),
    is_active: form.get("is_active") === "on",
  };
}

function failure(error: ApiError, data: ReturnType<typeof readForm>): FaqFormState {
  return {
    message: error.message,
    fields: error.fields,
    values: { ...data, is_active: data.is_active ? "on" : "" },
  };
}

// Las acciones solo reenvían a la API: el permiso de administrador lo comprueba Django.
async function mutate<T>(path: string, method: string, token: string, body?: unknown) {
  const result = await api<T>(path, { method, token, body });
  if (!result.ok && result.status === 401) {
    await clearToken();
    redirect(loginPath(result.error));
  }
  return result;
}

export async function createFaqAction(_: FaqFormState, form: FormData): Promise<FaqFormState> {
  const token = await requireToken();
  const data = readForm(form);
  const result = await mutate<Faq>("/api/faqs/", "POST", token, data);
  if (!result.ok) return failure(result.error, data);
  refresh();
  return { saved: true };
}

export async function updateFaqAction(
  id: number,
  _: FaqFormState,
  form: FormData,
): Promise<FaqFormState> {
  const token = await requireToken();
  const data = readForm(form);
  const result = await mutate<Faq>(`/api/faqs/${id}/`, "PUT", token, data);
  if (!result.ok) return failure(result.error, data);
  redirect("/admin/faqs");
}

export async function setFaqActiveAction(id: number, isActive: boolean): Promise<RowActionResult> {
  const token = await requireToken();
  const result = await mutate<Faq>(`/api/faqs/${id}/`, "PATCH", token, { is_active: isActive });
  if (!result.ok) return { ok: false, message: result.error.message };
  refresh();
  return { ok: true };
}

export async function deleteFaqAction(id: number): Promise<RowActionResult> {
  const token = await requireToken();
  const result = await mutate<null>(`/api/faqs/${id}/`, "DELETE", token);
  if (!result.ok) return { ok: false, message: result.error.message };
  refresh();
  return { ok: true };
}
