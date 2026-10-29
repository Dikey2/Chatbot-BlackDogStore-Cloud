import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import Link from "next/link";

export type DownReason = "unavailable" | "timeout" | "chatbot";

const KEYS: Record<DownReason, [string, string]> = {
  unavailable: ["down.backendTitle", "down.backendMessage"],
  timeout: ["down.timeoutTitle", "down.timeoutMessage"],
  chatbot: ["down.chatbotTitle", "down.chatbotMessage"],
};

/** Pantalla para caídas previstas: API sin respuesta, tiempo agotado o chatbot caído. */
export async function ServiceUnavailable({ reason, retryHref }: { reason: DownReason; retryHref: string }) {
  const locale = await getLocale();
  const [title, message] = KEYS[reason];
  return (
    <section className="down" role="alert" data-testid="service-unavailable" data-reason={reason}>
      <h2>{t(locale, title)}</h2>
      <p className="muted">{t(locale, message)}</p>
      <nav className="links">
        <Link href={retryHref}>{t(locale, "common.retry")}</Link>
        <Link href="/">{t(locale, "down.status")}</Link>
      </nav>
    </section>
  );
}
