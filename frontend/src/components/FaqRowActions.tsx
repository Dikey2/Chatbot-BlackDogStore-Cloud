"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { deleteFaqAction, setFaqActiveAction, type RowActionResult } from "@/app/admin/faqs/actions";

export function FaqRowActions({
  id,
  question,
  isActive,
}: {
  id: number;
  question: string;
  isActive: boolean;
}) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function run(action: () => Promise<RowActionResult>) {
    setError(null);
    startTransition(async () => {
      try {
        const result = await action();
        if (!result.ok) setError(result.message);
      } catch {
        setError("No se pudo conectar con el servidor.");
      }
    });
  }

  return (
    <div className="row-actions">
      <Link href={`/admin/faqs/${id}`}>Editar</Link>
      <button
        type="button"
        className="secondary"
        disabled={pending}
        onClick={() => run(() => setFaqActiveAction(id, !isActive))}
      >
        {isActive ? "Desactivar" : "Activar"}
      </button>
      <button
        type="button"
        className="danger"
        disabled={pending}
        onClick={() => {
          if (window.confirm(`¿Eliminar "${question}"? Esta acción no se puede deshacer.`)) {
            run(() => deleteFaqAction(id));
          }
        }}
      >
        Eliminar
      </button>
      {error && (
        <span className="error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
