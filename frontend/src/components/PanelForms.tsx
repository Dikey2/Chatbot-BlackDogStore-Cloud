"use client";

import { useActionState, useState, useTransition, type ReactNode } from "react";
import { useLocale } from "@/components/LocaleProvider";
import { t } from "@/lib/i18n";
import type { ActionResult, PanelFormState } from "@/app/panel/actions";

type FormAction = (state: PanelFormState, form: FormData) => Promise<PanelFormState>;

function Errors({ state, name }: { state: PanelFormState; name: string }) {
  return (
    <>
      {state.fields?.[name]?.map((message) => (
        <span key={message} className="error" role="alert">
          {message}
        </span>
      ))}
    </>
  );
}

/** Formulario con estado de envío, errores por campo y aviso de guardado. */
function PanelForm({
  action,
  submitLabel,
  savedLabel,
  resetOnSave = false,
  testId,
  children,
}: {
  action: FormAction;
  submitLabel: string;
  savedLabel: string;
  resetOnSave?: boolean;
  testId?: string;
  children: (state: PanelFormState) => ReactNode;
}) {
  const locale = useLocale();
  const [state, formAction, pending] = useActionState(action, {});
  const generalError = state.message && !Object.keys(state.fields ?? {}).length;
  return (
    <form
      action={formAction}
      className="form panel-form"
      data-testid={testId}
      key={resetOnSave ? state.sentAt ?? "form" : "form"}
    >
      {children(state)}
      {generalError && (
        <p className="error" role="alert">
          {state.message}
        </p>
      )}
      {state.message && Object.keys(state.fields ?? {}).length > 0 && (
        <p className="error" role="alert">
          {t(locale, "panel.fixErrors")}
        </p>
      )}
      {state.saved && (
        <p className="ok" role="status">
          {savedLabel}
        </p>
      )}
      <button type="submit" disabled={pending}>
        {pending ? t(locale, "faq.saving") : submitLabel}
      </button>
    </form>
  );
}

export type ConfigValues = {
  name: string;
  description: string;
  logo_url: string;
  assistant_name: string;
  welcome_message: string;
  no_answer_message: string;
  handoff_message: string;
  handoff_keywords: string;
  schedule: string;
  contact_info: string;
  primary_color: string;
  is_active: boolean;
};

export function ChatbotConfigForm({ action, initial }: { action: FormAction; initial: ConfigValues }) {
  const locale = useLocale();
  const field = (name: keyof ConfigValues, label: string, options: { long?: boolean; max?: number; help?: string } = {}) => (
    <label>
      {label}
      {options.long ? (
        <textarea name={name} rows={3} maxLength={options.max} defaultValue={String(initial[name])} />
      ) : (
        <input name={name} maxLength={options.max} defaultValue={String(initial[name])} />
      )}
      {options.help && <small className="muted">{options.help}</small>}
    </label>
  );
  return (
    <PanelForm action={action} submitLabel={t(locale, "panel.save")} savedLabel={t(locale, "panel.saved")} testId="config-form">
      {(state) => (
        <>
          <fieldset>
            <legend>{t(locale, "panel.businessData")}</legend>
            {field("name", t(locale, "common.name"), { max: 120 })}
            <Errors state={state} name="name" />
            {field("description", t(locale, "panel.description"), { long: true, max: 1000 })}
            {field("logo_url", t(locale, "panel.logo"), { max: 500, help: t(locale, "panel.logoHelp") })}
            <Errors state={state} name="logo_url" />
          </fieldset>
          <fieldset>
            <legend>{t(locale, "panel.assistant")}</legend>
            {field("assistant_name", t(locale, "panel.assistantName"), { max: 80 })}
            <Errors state={state} name="chatbot.assistant_name" />
            {field("welcome_message", t(locale, "panel.welcome"), { long: true, max: 300 })}
            {field("no_answer_message", t(locale, "panel.noAnswer"), { long: true, max: 300 })}
            {field("handoff_message", t(locale, "panel.handoffMessage"), { long: true, max: 300 })}
            {field("handoff_keywords", t(locale, "panel.handoffKeywords"), { max: 255, help: t(locale, "panel.handoffHelp") })}
            {field("schedule", t(locale, "panel.schedule"), { long: true, max: 500, help: t(locale, "panel.onlyConfigured") })}
            {field("contact_info", t(locale, "panel.contact"), { long: true, max: 500, help: t(locale, "panel.onlyConfigured") })}
            <label>
              {t(locale, "panel.color")}
              <input name="primary_color" type="color" defaultValue={initial.primary_color} />
            </label>
            <Errors state={state} name="chatbot.primary_color" />
            <label className="checkbox">
              <input type="checkbox" name="is_active" defaultChecked={initial.is_active} />
              {t(locale, "panel.chatbotActive")}
            </label>
          </fieldset>
        </>
      )}
    </PanelForm>
  );
}

export function DomainForm({ action }: { action: FormAction }) {
  const locale = useLocale();
  return (
    <PanelForm action={action} submitLabel={t(locale, "panel.addDomain")} savedLabel={t(locale, "panel.domainAdded")} resetOnSave testId="domain-form">
      {(state) => (
        <label>
          {t(locale, "panel.origin")}
          <input name="origin" placeholder="https://www.mi-negocio.com" required maxLength={255} />
          <Errors state={state} name="origin" />
        </label>
      )}
    </PanelForm>
  );
}

export function MemberForm({ action, allowAdmin = true }: { action: FormAction; allowAdmin?: boolean }) {
  const locale = useLocale();
  return (
    <PanelForm action={action} submitLabel={t(locale, "panel.addMember")} savedLabel={t(locale, "panel.memberAdded")} resetOnSave testId="member-form">
      {(state) => (
        <>
          <label>
            {t(locale, "common.email")}
            <input name="email" type="email" required maxLength={254} />
            <Errors state={state} name="email" />
          </label>
          <label>
            {t(locale, "common.name")}
            <input name="name" maxLength={150} />
          </label>
          <label>
            {t(locale, "panel.passwordNew")}
            <input name="password" type="password" autoComplete="new-password" maxLength={128} />
            <Errors state={state} name="password" />
          </label>
          {allowAdmin && (
            <label>
              {t(locale, "panel.role")}
              <select name="role" defaultValue="asesor">
                <option value="asesor">{t(locale, "common.advisor")}</option>
                <option value="admin">{t(locale, "panel.roleAdmin")}</option>
              </select>
            </label>
          )}
        </>
      )}
    </PanelForm>
  );
}

export function BusinessCreateForm({ action }: { action: FormAction }) {
  const locale = useLocale();
  return (
    <PanelForm action={action} submitLabel={t(locale, "platform.create")} savedLabel={t(locale, "platform.created")} resetOnSave testId="business-form">
      {(state) => (
        <>
          <label>
            {t(locale, "common.name")}
            <input name="name" required maxLength={120} />
            <Errors state={state} name="name" />
          </label>
          <label>
            Slug
            <input name="slug" required maxLength={60} pattern="[a-z0-9-]+" placeholder="mi-negocio" />
            <Errors state={state} name="slug" />
          </label>
          <label>
            {t(locale, "panel.description")}
            <textarea name="description" rows={2} maxLength={1000} />
          </label>
        </>
      )}
    </PanelForm>
  );
}

/** Botón que ejecuta una acción del servidor, con confirmación opcional y error visible. */
export function ActionButton({
  action,
  label,
  pendingLabel,
  confirmText,
  secondary = true,
  testId,
}: {
  action: () => Promise<ActionResult>;
  label: string;
  pendingLabel?: string;
  confirmText?: string;
  secondary?: boolean;
  testId?: string;
}) {
  const locale = useLocale();
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  return (
    <span className="action-button">
      <button
        type="button"
        className={secondary ? "secondary" : undefined}
        disabled={pending}
        data-testid={testId}
        onClick={() => {
          if (confirmText && !window.confirm(confirmText)) return;
          setError(null);
          start(async () => {
            try {
              const result = await action();
              if (!result.ok) setError(result.message);
            } catch {
              setError(t(locale, "common.sessionError"));
            }
          });
        }}
      >
        {pending ? pendingLabel ?? "…" : label}
      </button>
      {error && (
        <span className="error" role="alert">
          {error}
        </span>
      )}
    </span>
  );
}

/** Código de instalación con botón de copiar. */
export function InstallSnippet({ code }: { code: string }) {
  const locale = useLocale();
  const [copied, setCopied] = useState(false);
  return (
    <div className="snippet">
      <pre data-testid="install-snippet">
        <code>{code}</code>
      </pre>
      <button
        type="button"
        className="secondary"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          } catch {
            setCopied(false);
          }
        }}
      >
        {copied ? t(locale, "panel.copied") : t(locale, "panel.copy")}
      </button>
    </div>
  );
}
