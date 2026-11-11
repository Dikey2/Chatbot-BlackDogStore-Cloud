import type { Metadata } from "next";
import Script from "next/script";
import { publicApiUrl } from "@/lib/api";
import { WidgetLoadCheck } from "@/components/WidgetLoadCheck";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

export const metadata: Metadata = { title: "Vista previa del widget" };

/**
 * Página neutra para probar el widget de un negocio antes de instalarlo.
 * El origen del panel está en WIDGET_PREVIEW_ORIGINS, así que puede cargar
 * cualquier widget; el id público no es un secreto.
 */
export default async function PreviewPage({ searchParams }: PageProps<"/vista-previa">) {
  const locale = await getLocale();
  const { id } = await searchParams;
  const publicId = typeof id === "string" && /^[A-Za-z0-9_-]{4,40}$/.test(id) ? id : null;
  const api = publicApiUrl();
  return (
    <main className="wide">
      <h1>{t(locale, "preview.title")}</h1>
      <p className="muted">{t(locale, "preview.intro")}</p>
      {publicId && !api.url ? (
        <p className="error" role="alert" data-testid="public-url-missing">
          {api.problem}
        </p>
      ) : publicId && api.url ? (
        <>
          <p>
            <code data-testid="preview-id">{publicId}</code>
          </p>
          <Script src={`${api.url}/widget.js`} data-chatbot-id={publicId} strategy="afterInteractive" />
          <WidgetLoadCheck scriptUrl={`${api.url}/widget.js`} />
        </>
      ) : (
        <p className="error" role="alert">
          {t(locale, "preview.missing")}
        </p>
      )}
    </main>
  );
}
