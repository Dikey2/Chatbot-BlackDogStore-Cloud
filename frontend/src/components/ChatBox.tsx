"use client";

import { useState, type FormEvent } from "react";
import { sendMessageAction } from "@/app/actions";
import type { ChatMessage } from "@/lib/chat";

const SENDER_LABELS = { cliente: "Tú", bot: "Chatbot", asesor: "Asesor" } as const;

const MAX_LENGTH = 500;
const CONNECTION_ERROR = "No se pudo conectar con el servidor. Revisa tu conexión e inténtalo otra vez.";

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
        setError(reply.message);
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
      setError(CONNECTION_ERROR);
    } finally {
      setPending(false);
    }
  }

  return (
    <section>
      <ol className="messages" aria-live="polite" data-testid="messages">
        {messages.length === 0 && (
          <li className="muted">Escribe tu consulta para comenzar.</li>
        )}
        {messages.map((message) => (
          <li
            key={message.id}
            className={`message ${message.sender}`}
            data-sender={message.sender}
          >
            {message.sender === "asesor" && <span className="sender">{SENDER_LABELS.asesor}</span>}
            {message.content}
          </li>
        ))}
      </ol>
      {closed && (
        <p className="muted" data-testid="conversation-closed">
          Un asesor cerró esta conversación. Tu próximo mensaje iniciará una nueva.
        </p>
      )}
      {escalated && (
        <p className="muted" data-testid="escalated">
          Tu consulta fue derivada a un asesor.
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <form onSubmit={handleSubmit} className="chat-form">
        <input
          aria-label="Mensaje"
          value={text}
          onChange={(event) => setText(event.target.value)}
          maxLength={MAX_LENGTH}
          placeholder="Por ejemplo: ¿cuál es el horario?"
          autoComplete="off"
        />
        <button type="submit" disabled={pending || !text.trim()}>
          {pending ? "Enviando…" : "Enviar"}
        </button>
      </form>
    </section>
  );
}
