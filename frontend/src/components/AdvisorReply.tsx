"use client";
import { useLocale } from "@/components/LocaleProvider";
import { t } from "@/lib/i18n";


import { useActionState, useState, useTransition } from "react";
import { closeAction, type ReplyState } from "@/app/asesor/actions";

export function AdvisorReply({
  conversationId,
  action,
}: {
  conversationId: number;
  action: (state: ReplyState, form: FormData) => Promise<ReplyState>;
}) {
  const locale = useLocale();
  const [state, formAction, pending] = useActionState(action, {});
  const [closing, startClosing] = useTransition();
  const [closeError, setCloseError] = useState<string | null>(null);

  function close() {
    if (!window.confirm(t(locale, "advisor.closeConfirm"))) return;
    setCloseError(null);
    startClosing(async () => {
      try {
        const result = await closeAction(conversationId);
        if (!result.ok) setCloseError(result.message ?? t(locale, "advisor.closeError"));
      } catch {
        setCloseError(t(locale, "common.sessionError"));
      }
    });
  }

  return (
    <>
      <form action={formAction} className="form" key={state.sentAt ?? "reply"}>
        <label>
          {t(locale, "advisor.reply")}
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
            {t(locale, "advisor.replySent")}
          </p>
        )}
        <div className="row-actions">
          <button type="submit" disabled={pending || closing}>
            {pending ? t(locale, "common.sending") : t(locale, "advisor.replyButton")}
          </button>
          <button type="button" className="secondary" onClick={close} disabled={pending || closing}>
            {closing ? t(locale, "advisor.closing") : t(locale, "advisor.close")}
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
