"use client";

import { useEffect, useState } from "react";
import { useLocale } from "@/components/LocaleProvider";
import { t } from "@/lib/i18n";

/**
 * Vista previa: si a los 20 s el widget no apareció, explica qué revisar en vez
 * de dejar la página vacía. El widget reintenta su configuración hasta ~30 s.
 */
export function WidgetLoadCheck({ scriptUrl }: { scriptUrl: string }) {
  const locale = useLocale();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!document.querySelector("[data-bd-chatbot]")) setFailed(true);
    }, 20000);
    return () => window.clearTimeout(timer);
  }, []);
  if (!failed) return null;
  return (
    <div className="error" role="alert" data-testid="widget-load-failed">
      <p>{t(locale, "preview.failed")}</p>
      <ul>
        <li>{t(locale, "preview.checkScript", { url: scriptUrl })}</li>
        <li>{t(locale, "preview.checkOrigin")}</li>
        <li>{t(locale, "preview.checkActive")}</li>
      </ul>
    </div>
  );
}
