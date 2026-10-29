"use client";
import { useLocale } from "@/components/LocaleProvider";
import { t } from "@/lib/i18n";


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
  const locale = useLocale();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function run(action: () => Promise<RowActionResult>) {
    setError(null);
    startTransition(async () => {
      try {
        const result = await action();
        if (!result.ok) setError(result.message);
      } catch {
        setError(t(locale, "common.sessionError"));
      }
    });
  }

  return (
    <div className="row-actions">
      <Link href={`/admin/faqs/${id}`}>{t(locale, "faq.edit")}</Link>
      <button
        type="button"
        className="secondary"
        disabled={pending}
        onClick={() => run(() => setFaqActiveAction(id, !isActive))}
      >
        {t(locale, isActive ? "faq.deactivate" : "faq.activate")}
      </button>
      <button
        type="button"
        className="danger"
        disabled={pending}
        onClick={() => {
          if (window.confirm(t(locale, "faq.deleteConfirm", { question }))) {
            run(() => deleteFaqAction(id));
          }
        }}
      >
        {t(locale, "faq.delete")}
      </button>
      {error && (
        <span className="error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
