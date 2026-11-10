import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { PanelNav } from "@/components/PanelNav";
import { getMetrics } from "@/lib/business";
import { STATUS_KEYS, type ConversationStatus } from "@/lib/chat";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { User } from "@/lib/session";

export const metadata: Metadata = { title: "Panel del negocio" };

async function Dashboard({ token, user }: { token: string; user: User }) {
  const locale = await getLocale();
  if (user.role !== "admin") {
    return (
      <p>
        {t(locale, "panel.advisorHome")} <Link href="/asesor">{t(locale, "home.advisor")}</Link>
      </p>
    );
  }
  const result = await getMetrics(token);
  if (!result.ok) {
    return (
      <p className="error" role="alert">
        {result.error.message}
      </p>
    );
  }
  const m = result.data;
  const cards: [string, number][] = [
    [t(locale, "panel.metric.conversations"), m.conversations_total],
    [t(locale, "panel.metric.week"), m.conversations_last_7_days],
    [t(locale, "panel.metric.widget"), m.widget_conversations],
    [t(locale, "panel.metric.messages"), m.messages_total],
    [t(locale, "panel.metric.faqs"), m.faqs_active],
    [t(locale, "panel.metric.domains"), m.domains ?? 0],
  ];
  return (
    <>
      <ul className="metrics" data-testid="metrics">
        {cards.map(([label, value]) => (
          <li key={label}>
            <strong>{value}</strong>
            <span className="muted">{label}</span>
          </li>
        ))}
      </ul>
      <h2>{t(locale, "panel.byStatus")}</h2>
      <ul className="status">
        {(Object.keys(STATUS_KEYS) as ConversationStatus[]).map((status) => (
          <li key={status}>
            <Link href={`/asesor?estado=${status}`}>{t(locale, STATUS_KEYS[status])}</Link>
            <span>{m.conversations_by_status[status] ?? 0}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

async function Content() {
  const locale = await getLocale();
  return (
    <RoleGate roles={["admin", "asesor"]} forbiddenMessage={t(locale, "panel.forbidden")} retryHref="/panel">
      {async (token, user) => (
        <>
          <PanelNav user={user} current="/panel" />
          <Dashboard token={token} user={user} />
        </>
      )}
    </RoleGate>
  );
}

export default async function PanelPage() {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "panel.title")}</h1>
      <p className="muted">{t(locale, "panel.intro")}</p>
      <Suspense fallback={<p className="muted">{t(locale, "common.loading")}</p>}>
        <Content />
      </Suspense>
    </main>
  );
}
