import "server-only";
import { api, type ApiResult } from "./api";

export type ChatMessage = {
  id: number;
  sender: "cliente" | "bot" | "asesor";
  content: string;
  created_at: string;
};

export type ConversationStatus = "abierta" | "derivada" | "atendiendo" | "cerrada";

export type Conversation = {
  id: number;
  user: number | null;
  user_name: string;
  channel?: "widget" | "plataforma";
  assigned_to?: number | null;
  assigned_to_name?: string | null;
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
/** Vista de la bandeja: un estado, o "mias" (las asignadas al asesor, en cualquier estado). */
export type InboxView = ConversationStatus | "mias";

export function listConversations(
  token: string,
  view: InboxView,
  page: number,
): Promise<ApiResult<ConversationPage>> {
  const filter = view === "mias" ? "assigned=me" : `status=${view}`;
  return api<ConversationPage>(`/api/chat/conversations/?${filter}&page=${page}`, { token });
}

export function getConversation(token: string, id: number): Promise<ApiResult<ConversationDetail>> {
  return api<ConversationDetail>(`/api/chat/conversations/${id}/`, { token });
}

export const STATUS_LABELS: Record<ConversationStatus, string> = {
  derivada: "Derivadas",
  atendiendo: "En atención",
  abierta: "Abiertas",
  cerrada: "Cerradas",
};

/** Clave de i18n de cada estado. */
export const STATUS_KEYS: Record<ConversationStatus, string> = {
  derivada: "advisor.escalated",
  atendiendo: "advisor.attending",
  abierta: "advisor.open",
  cerrada: "advisor.closed",
};

export const SENDER_LABELS: Record<ChatMessage["sender"], string> = {
  cliente: "Cliente",
  bot: "Chatbot",
  asesor: "Asesor",
};
