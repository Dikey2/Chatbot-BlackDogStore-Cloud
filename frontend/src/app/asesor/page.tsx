import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { listConversations, STATUS_LABELS, type ConversationStatus } from "@/lib/chat";

export const metadata: Metadata = { title: "Bandeja del asesor" };

const STATUSES = Object.keys(STATUS_LABELS) as ConversationStatus[];

async function Inbox({ token, status, page }: { token: string; status: ConversationStatus; page: number }) {
  const locale = await getLocale();
  const result = await listConversations(token, status, page);
  if (!result.ok) {
    return (
      <p className="error" role="alert">
        {result.status === 404 ? t(locale, "faq.missingPage") : result.error.message}{" "}
        <Link href={`/asesor?estado=${status}`}>{t(locale, "faq.firstPage")}</Link>
      </p>
    );
  }
  const { count, next, previous, results } = result.data;
  if (count === 0) return <p className="muted">{t(locale, "advisor.empty")}</p>;
  return (
    <>
      <div className="table-wrap">
        <table className="table" data-testid="inbox-table">
          <thead>
            <tr>
              <th>{t(locale, "advisor.number")}</th>
              <th>{t(locale, "common.client")}</th>
              <th>{t(locale, "advisor.start")}</th>
              <th>{t(locale, "common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {results.map((conversation) => (
              <tr key={conversation.id}>
                <td>{conversation.id}</td>
                <td>{conversation.user_name}</td>
                <td>{new Intl.DateTimeFormat(locale === "en" ? "en-US" : "es-PE", { dateStyle: "short", timeStyle: "short", timeZone: "America/Lima" }).format(new Date(conversation.created_at))}</td>
                <td>
                  <Link href={`/asesor/${conversation.id}`}>{t(locale, "advisor.view")}</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <nav className="links" aria-label="Paginación">
        {previous && <Link href={`/asesor?estado=${status}&page=${page - 1}`}>{t(locale, "common.previous")}</Link>}
        <span className="muted">
          {t(locale, "common.page")} {page} · {t(locale, "advisor.total", { count })}
        </span>
        {next && <Link href={`/asesor?estado=${status}&page=${page + 1}`}>{t(locale, "common.next")}</Link>}
      </nav>
    </>
  );
}

async function AdvisorInbox({ searchParams }: { searchParams: PageProps<"/asesor">["searchParams"] }) {
  const locale = await getLocale();
  const { estado, page } = await searchParams;
  const status = STATUSES.includes(estado as ConversationStatus) ? (estado as ConversationStatus) : "derivada";
  const pageNumber = Math.max(1, Number.parseInt(String(page ?? "1"), 10) || 1);
  return (
    <RoleGate
      roles={["asesor", "admin"]}
      forbiddenMessage={t(locale, "advisor.forbidden")}
      retryHref="/asesor"
    >
      {async (token) => (
        <>
          <nav className="tabs" aria-label="Estado">
            {STATUSES.map((value) => (
              <Link key={value} href={`/asesor?estado=${value}`} aria-current={value === status ? "page" : undefined}>
                {t(locale, value === "derivada" ? "advisor.escalated" : value === "abierta" ? "advisor.open" : "advisor.closed")}
              </Link>
            ))}
          </nav>
          <Inbox token={token} status={status} page={pageNumber} />
        </>
      )}
    </RoleGate>
  );
}

export default async function AdvisorPage({ searchParams }: PageProps<"/asesor">) {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "advisor.title")}</h1>
      <p className="muted">
        {t(locale, "advisor.intro")}
      </p>
      <p>
        <Link href="/chat">{t(locale, "common.backChat")}</Link>
      </p>
      <Suspense fallback={<p className="muted">{t(locale, "advisor.loading")}</p>}>
        <AdvisorInbox searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
