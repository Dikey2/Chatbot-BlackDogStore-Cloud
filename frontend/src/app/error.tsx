"use client";
import { useLocale } from "@/components/LocaleProvider";
import { t } from "@/lib/i18n";


export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  const locale = useLocale();
  return (
    <main>
      <h1>{t(locale, "error.title")}</h1>
      <p className="muted">{t(locale, "error.message")}</p>
      <button onClick={reset}>{t(locale, "common.retry")}</button>
    </main>
  );
}
