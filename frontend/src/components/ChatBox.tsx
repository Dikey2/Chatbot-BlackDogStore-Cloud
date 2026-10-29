"use client";
import { useLocale } from "@/components/LocaleProvider";
import { t } from "@/lib/i18n";


import { useState, type FormEvent } from "react";
import { sendMessageAction } from "@/app/actions";
import type { ChatMessage } from "@/lib/chat";

const MAX_LENGTH = 500;
// Errores previstos con texto propio en ambos idiomas; el resto muestra el mensaje de la API.
const KNOWN_ERRORS = new Set(["chatbot_unavailable", "timeout", "unavailable", "throttled", "server_error"]);

export function ChatBox({
  initialConversationId = null,
  initialMessages = [],
  initialEscalated = false,
  initialClosed = false,
}: {
  initialConversationId?: number | null;
  initialMessages?: ChatMessage[];
  initialEscalated?: boolean;
  initialClosed?: boolean;
}) {
  const locale = useLocale();
  // El historial llega del servidor (PostgreSQL); el estado local solo agrega lo nuevo.
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  // Una conversación cerrada por el asesor no se continúa: el siguiente mensaje abre otra.
  const [conversationId, setConversationId] = useState<number | null>(
    initialClosed ? null : initialConversationId,
  );
  const [closed, setClosed] = useState(initialClosed);
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [escalated, setEscalated] = useState(initialEscalated && !initialClosed);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const message = text.trim();
    if (!message || pending) return;
    setPending(true);
    setError(null);
    try {
      const reply = await sendMessageAction(message, conversationId);
      if (!reply.ok) {
        setError(KNOWN_ERRORS.has(reply.code) ? t(locale, `errors.${reply.code}`) : reply.message);
        return;
      }
      setText("");
      if (closed) {
        // Empieza la conversación nueva: se deja de mostrar la anterior.
        setClosed(false);
        setMessages([]);
      }
      setConversationId(reply.conversationId);
      setEscalated((previous) => previous || reply.escalated);
      setMessages((previous) => [...previous, reply.userMessage, reply.botMessage]);
    } catch {
      // Falla la red entre el navegador y el servidor web. El texto se conserva.
      setError(t(locale, "chat.netError"));
    } finally {
      setPending(false);
    }
  }

  return (
    <section>
      <ol className="messages" aria-live="polite" data-testid="messages">
        {messages.length === 0 && (
          <li className="muted">{t(locale, "chat.start")}</li>
        )}
        {messages.map((message) => (
          <li
            key={message.id}
            className={`message ${message.sender}`}
            data-sender={message.sender}
          >
            {message.sender === "asesor" && <span className="sender">{t(locale, "common.advisor")}</span>}
            {message.content}
          </li>
        ))}
      </ol>
      {closed && (
        <p className="muted" data-testid="conversation-closed">
          {t(locale, "chat.closed")}
        </p>
      )}
      {escalated && (
        <p className="muted" data-testid="escalated">
          {t(locale, "chat.escalated")}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <form onSubmit={handleSubmit} className="chat-form">
        <input
          aria-label={t(locale, "chat.message")}
          value={text}
          onChange={(event) => setText(event.target.value)}
          maxLength={MAX_LENGTH}
          placeholder={t(locale, "chat.placeholder")}
          autoComplete="off"
        />
        <button type="submit" disabled={pending || !text.trim()}>
          {pending ? t(locale, "common.sending") : t(locale, "chat.send")}
        </button>
      </form>
    </section>
  );
}
