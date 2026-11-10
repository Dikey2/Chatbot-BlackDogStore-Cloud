import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { PanelNav } from "@/components/PanelNav";
import { listPlatformAudit } from "@/lib/audit";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

export const metadata: Metadata = { title: "Auditoría de la plataforma" };

type Scope = "todos" | "plataforma";

function href(scope: Scope, page: number) {
  const query = new URLSearchParams();
  if (scope === "plataforma") query.set("alcance", "plataforma");
  if (page > 1) query.set("page", String(page));
  const text = query.toString();
  return text ? `/plataforma/auditoria?${text}` : "/plataforma/auditoria";
}

async function Events({ token, scope, page }: { token: string; scope: Scope; page: number }) {
  const locale = await getLocale();
  const result = await listPlatformAudit(token, { scope, page });
  if (!result.ok) {
    return (
      <p className="error" role="alert">
        {result.error.message}
      </p>
    );
  }
  const { count, next, previous, results } = result.data;
  if (count === 0) return <p className="muted">{t(locale, "audit.empty")}</p>;
  const format = new Intl.DateTimeFormat(locale === "en" ? "en-US" : "es-PE", {
    dateStyle: "short",
    timeStyle: "medium",
    timeZone: "America/Lima",
  });
  return (
    <>
      <p className="muted">{t(locale, "audit.total", { count })}</p>
      <div className="table-wrap">
        <table className="table" data-testid="platform-audit-table">
          <thead>
            <tr>
              <th>{t(locale, "audit.date")}</th>
              <th>{t(locale, "platform.business")}</th>
              <th>{t(locale, "audit.action")}</th>
              <th>{t(locale, "audit.result")}</th>
              <th>{t(locale, "audit.user")}</th>
              <th>{t(locale, "audit.source")}</th>
              <th>{t(locale, "audit.detail")}</th>
            </tr>
          </thead>
          <tbody>
            {results.map((event) => (
              <tr key={event.id} data-action={event.action}>
                <td>{format.format(new Date(event.created_at))}</td>
                <td>{event.business_name ?? <span className="muted">{t(locale, "platform.title")}</span>}</td>
                <td>{t(locale, `audit.action.${event.action}`)}</td>
                <td className={event.result === "exito" ? "ok" : "error"}>{t(locale, `audit.result.${event.result}`)}</td>
                <td>{event.user_name ? `${event.user_name} (${event.email})` : event.email || "—"}</td>
                <td>{event.source || "—"}</td>
                <td>{event.detail || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <nav className="links" aria-label="Paginación">
        {previous && <Link href={href(scope, page - 1)}>{t(locale, "common.previous")}</Link>}
        <span className="muted">
          {t(locale, "common.page")} {page}
        </span>
        {next && <Link href={href(scope, page + 1)}>{t(locale, "common.next")}</Link>}
      </nav>
    </>
  );
}

async function Content({ searchParams }: { searchParams: PageProps<"/plataforma/auditoria">["searchParams"] }) {
  const locale = await getLocale();
  const { alcance, page } = await searchParams;
  const scope: Scope = alcance === "plataforma" ? "plataforma" : "todos";
  const pageNumber = Math.max(1, Number.parseInt(String(page ?? "1"), 10) || 1);
  return (
    <RoleGate roles={["plataforma"]} forbiddenMessage={t(locale, "platform.forbidden")} retryHref="/plataforma/auditoria">
      {async (token, user) => (
        <>
          <PanelNav user={user} current="/plataforma/auditoria" />
          <nav className="tabs" aria-label={t(locale, "platform.audit")}>
            <Link href={href("todos", 1)} aria-current={scope === "todos" ? "page" : undefined}>
              {t(locale, "platform.auditAll")}
            </Link>
            <Link href={href("plataforma", 1)} aria-current={scope === "plataforma" ? "page" : undefined}>
              {t(locale, "platform.auditPlatform")}
            </Link>
          </nav>
          <Events token={token} scope={scope} page={pageNumber} />
        </>
      )}
    </RoleGate>
  );
}

export default async function PlatformAuditPage({ searchParams }: PageProps<"/plataforma/auditoria">) {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "platform.audit")}</h1>
      <p className="muted">{t(locale, "audit.intro")}</p>
      <Suspense fallback={<p className="muted">{t(locale, "common.loading")}</p>}>
        <Content searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
