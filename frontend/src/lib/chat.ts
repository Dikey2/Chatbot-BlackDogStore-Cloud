import "server-only";
import { api, type ApiResult } from "./api";

export type ChatMessage = {
  id: number;
  sender: "cliente" | "bot" | "asesor";
  content: string;
  created_at: string;
};

export type ConversationDetail = {
  id: number;
  status: "abierta" | "derivada" | "cerrada";
  created_at: string;
  messages: ChatMessage[];
};

/** Última conversación propia del usuario, o null si aún no tiene ninguna. */
export function getLatestConversation(token: string): Promise<ApiResult<ConversationDetail | null>> {
  return api<ConversationDetail | null>("/api/chat/conversations/latest/", { token });
}
