"use client";

import { useActionState } from "react";
import type { FormState } from "@/app/actions";

type Field = {
  name: string;
  label: string;
  type: string;
  autoComplete: string;
};

export function AuthForm({
  action,
  fields,
  submitLabel,
}: {
  action: (state: FormState, form: FormData) => Promise<FormState>;
  fields: Field[];
  submitLabel: string;
}) {
  const [state, formAction, pending] = useActionState(action, {});
  // Errores que la API no asocia a un campo visible (por ejemplo, contraseña débil).
  const general = Object.entries(state.fields ?? {})
    .filter(([name]) => !fields.some((field) => field.name === name))
    .flatMap(([, messages]) => messages);

  return (
    <form action={formAction} className="form">
      {fields.map((field) => (
        <label key={field.name}>
          {field.label}
          <input
            name={field.name}
            type={field.type}
            autoComplete={field.autoComplete}
            defaultValue={state.values?.[field.name] ?? ""}
            required
          />
          {state.fields?.[field.name]?.map((message) => (
            <span key={message} className="error" role="alert">
              {message}
            </span>
          ))}
        </label>
      ))}
      {state.message && (
        <p className="error" role="alert" data-testid="form-error">
          {state.message}
        </p>
      )}
      {general.map((message) => (
        <p key={message} className="error" role="alert">
          {message}
        </p>
      ))}
      <button type="submit" disabled={pending}>
        {pending ? "Enviando…" : submitLabel}
      </button>
    </form>
  );
}
