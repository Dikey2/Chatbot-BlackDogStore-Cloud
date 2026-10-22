"use server";

import { refresh } from "next/cache";
import { redirect } from "next/navigation";
import { api } from "@/lib/api";
import { clearToken, getToken, loginPath } from "@/lib/session";

export type ReplyState = { message?: string; fields?: Record<string, string[]>; value?: string; sentAt?: number };

async function staffRequest(path: string, body?: unknown) {
  const token = await getToken();
  if (!token) redirect("/login");
  // El permiso de asesor o administrador lo comprueba Django.
  const result = await api(path, { method: "POST", token, body });
  if (!result.ok && result.status === 401) {
    await clearToken();
    redirect(loginPath(result.error));
  }
  return result;
}

export async function replyAction(id: number, _: ReplyState, form: FormData): Promise<ReplyState> {
  const message = String(form.get("message") ?? "").trim();
  const result = await staffRequest(`/api/chat/conversations/${id}/reply/`, { message });
  if (!result.ok) {
    return { message: result.error.message, fields: result.error.fields, value: message };
  }
  refresh();
  // Marca del envío: el formulario la usa como key para vaciarse.
  return { sentAt: Date.now() };
}

export async function closeAction(id: number): Promise<{ ok: boolean; message?: string }> {
  const result = await staffRequest(`/api/chat/conversations/${id}/close/`);
  if (!result.ok) return { ok: false, message: result.error.message };
  refresh();
  return { ok: true };
}
