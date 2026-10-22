"use server";

import { redirect } from "next/navigation";
import { api, type ApiError } from "@/lib/api";
import type { ChatMessage } from "@/lib/chat";
import { clearToken, getToken, loginPath, saveToken, type User } from "@/lib/session";

export type FormState = {
  message?: string;
  fields?: Record<string, string[]>;
  values?: Record<string, string>;
};

function failure(error: ApiError, values: Record<string, string>): FormState {
  return { message: error.message, fields: error.fields, values };
}

async function login(email: string, password: string) {
  const result = await api<{ token: string; expires_at: string; user: User }>("/api/auth/login/", {
    method: "POST",
    body: { email, password },
  });
  if (result.ok) await saveToken(result.data.token, result.data.expires_at);
  return result;
}

export async function loginAction(_: FormState, form: FormData): Promise<FormState> {
  const email = String(form.get("email") ?? "");
  const result = await login(email, String(form.get("password") ?? ""));
  if (!result.ok) return failure(result.error, { email });
  redirect("/chat");
}

export async function registerAction(_: FormState, form: FormData): Promise<FormState> {
  const name = String(form.get("name") ?? "");
  const email = String(form.get("email") ?? "");
  const password = String(form.get("password") ?? "");
  const created = await api<User>("/api/auth/register/", {
    method: "POST",
    body: { name, email, password },
  });
  if (!created.ok) return failure(created.error, { name, email });
  const session = await login(email, password);
  // La cuenta ya existe; si el inicio automático falla, se entra por /login.
  redirect(session.ok ? "/chat" : "/login");
}

export async function logoutAction() {
  const token = await getToken();
  if (token) await api("/api/auth/logout/", { method: "POST", token });
  await clearToken();
  redirect("/");
}

export type ChatReply =
  | {
      ok: true;
      conversationId: number;
      userMessage: ChatMessage;
      botMessage: ChatMessage;
      escalated: boolean;
    }
  | { ok: false; message: string };

type MessageResponse = {
  conversation: { id: number };
  user_message: ChatMessage;
  bot_message: ChatMessage;
  escalated: boolean;
};

export async function sendMessageAction(
  message: string,
  conversationId: number | null,
): Promise<ChatReply> {
  const token = await getToken();
  if (!token) redirect("/login");
  const result = await api<MessageResponse>("/api/chat/messages/", {
    method: "POST",
    token,
    body: conversationId ? { message, conversation_id: conversationId } : { message },
  });
  if (result.ok) {
    return {
      ok: true,
      conversationId: result.data.conversation.id,
      userMessage: result.data.user_message,
      botMessage: result.data.bot_message,
      escalated: result.data.escalated,
    };
  }
  if (result.status === 401) {
    await clearToken();
    redirect(loginPath(result.error));
  }
  const fieldError = result.error.fields?.message?.[0];
  return { ok: false, message: fieldError ?? result.error.message };
}
