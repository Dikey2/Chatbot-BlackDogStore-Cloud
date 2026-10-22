"use client";

import { useActionState, useEffect, useRef } from "react";
import type { FaqFormState } from "@/app/admin/faqs/actions";

type Values = {
  category: string;
  question: string;
  answer: string;
  keywords: string;
  is_active: boolean;
};

const EMPTY: Values = { category: "", question: "", answer: "", keywords: "", is_active: true };

export function FaqForm({
  action,
  initial = EMPTY,
  submitLabel,
}: {
  action: (state: FaqFormState, form: FormData) => Promise<FaqFormState>;
  initial?: Values;
  submitLabel: string;
}) {
  const [state, formAction, pending] = useActionState(action, {});
  const formRef = useRef<HTMLFormElement>(null);

  // Tras crear una FAQ el formulario queda vacío para la siguiente.
  useEffect(() => {
    if (state.saved) formRef.current?.reset();
  }, [state]);

  // Tras un error se muestran los valores enviados, no los iniciales.
  const values = state.values;
  const value = (name: keyof Values) => values?.[name] ?? String(initial[name]);
  const errors = (name: string) =>
    state.fields?.[name]?.map((message) => (
      <span key={message} className="error" role="alert">
        {message}
      </span>
    ));

  return (
    <form
      ref={formRef}
      action={formAction}
      className="form"
      // Cambia la key tras cada envío para que los defaultValue se apliquen de nuevo.
      key={JSON.stringify(values ?? state.saved ?? "")}
    >
      <label>
        Categoría
        <input name="category" defaultValue={value("category")} maxLength={50} required />
        {errors("category")}
      </label>
      <label>
        Pregunta
        <input name="question" defaultValue={value("question")} maxLength={255} required />
        {errors("question")}
      </label>
      <label>
        Respuesta
        <textarea name="answer" defaultValue={value("answer")} rows={3} required />
        {errors("answer")}
      </label>
      <label>
        Palabras clave (separadas por coma)
        <input name="keywords" defaultValue={value("keywords")} maxLength={255} required />
        {errors("keywords")}
      </label>
      <label className="checkbox">
        <input
          type="checkbox"
          name="is_active"
          defaultChecked={values ? values.is_active === "on" : initial.is_active}
        />
        Activa (visible para clientes y para el chatbot)
      </label>
      {state.message && (
        <p className="error" role="alert" data-testid="faq-form-error">
          {state.message}
        </p>
      )}
      {state.saved && (
        <p className="ok" role="status">
          Pregunta frecuente creada.
        </p>
      )}
      <button type="submit" disabled={pending}>
        {pending ? "Guardando…" : submitLabel}
      </button>
    </form>
  );
}
