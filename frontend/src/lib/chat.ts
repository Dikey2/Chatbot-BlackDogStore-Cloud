import "server-only";
import { api, type ApiResult } from "./api";

export type ChatMessage = {
  id: number;
  sender: "cliente" | "bot" | "asesor";
  content: string;
  created_at: string;
};

export type ConversationStatus = "abierta" | "derivada" | "cerrada";

export type Conversation = {
  id: number;
  user: number;
  user_name: string;
  status: ConversationStatus;
  created_at: string;
};

export type ConversationDetail = Conversation & { messages: ChatMessage[] };

export type ConversationPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Conversation[];
};

/** Última conversación propia del usuario, o null si aún no tiene ninguna. */
export function getLatestConversation(token: string): Promise<ApiResult<ConversationDetail | null>> {
  return api<ConversationDetail | null>("/api/chat/conversations/latest/", { token });
}

/** Bandeja del asesor: la API devuelve todas las conversaciones solo a asesor y admin. */
export function listConversations(
  token: string,
  status: ConversationStatus,
  page: number,
): Promise<ApiResult<ConversationPage>> {
  return api<ConversationPage>(`/api/chat/conversations/?status=${status}&page=${page}`, { token });
}

export function getConversation(token: string, id: number): Promise<ApiResult<ConversationDetail>> {
  return api<ConversationDetail>(`/api/chat/conversations/${id}/`, { token });
}

export const STATUS_LABELS: Record<ConversationStatus, string> = {
  derivada: "Derivadas",
  abierta: "Abiertas",
  cerrada: "Cerradas",
};

export const SENDER_LABELS: Record<ChatMessage["sender"], string> = {
  cliente: "Cliente",
  bot: "Chatbot",
  asesor: "Asesor",
};
