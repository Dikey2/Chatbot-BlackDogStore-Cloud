"use client";

import { useActionState, useState, useTransition } from "react";
import { closeAction, type ReplyState } from "@/app/asesor/actions";

export function AdvisorReply({
  conversationId,
  action,
}: {
  conversationId: number;
  action: (state: ReplyState, form: FormData) => Promise<ReplyState>;
}) {
  const [state, formAction, pending] = useActionState(action, {});
  const [closing, startClosing] = useTransition();
  const [closeError, setCloseError] = useState<string | null>(null);

  function close() {
    if (!window.confirm("¿Cerrar la conversación? El cliente empezará una nueva si vuelve a escribir.")) return;
    setCloseError(null);
    startClosing(async () => {
      try {
        const result = await closeAction(conversationId);
        if (!result.ok) setCloseError(result.message ?? "No se pudo cerrar.");
      } catch {
        setCloseError("No se pudo conectar con el servidor.");
      }
    });
  }

  return (
    <>
      <form action={formAction} className="form" key={state.sentAt ?? "reply"}>
        <label>
          Respuesta al cliente
          <textarea name="message" rows={3} maxLength={2000} defaultValue={state.value ?? ""} required />
          {state.fields?.message?.map((message) => (
            <span key={message} className="error" role="alert">
              {message}
            </span>
          ))}
        </label>
        {state.message && !state.fields && (
          <p className="error" role="alert">
            {state.message}
          </p>
        )}
        {state.sentAt && (
          <p className="ok" role="status">
            Respuesta enviada.
          </p>
        )}
        <div className="row-actions">
          <button type="submit" disabled={pending || closing}>
            {pending ? "Enviando…" : "Responder"}
          </button>
          <button type="button" className="secondary" onClick={close} disabled={pending || closing}>
            {closing ? "Cerrando…" : "Cerrar conversación"}
          </button>
        </div>
      </form>
      {closeError && (
        <p className="error" role="alert">
          {closeError}
        </p>
      )}
    </>
  );
}
