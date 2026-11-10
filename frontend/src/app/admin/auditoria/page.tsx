import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { AUDIT_ACTIONS, AUDIT_RESULTS, listAudit, type AuditAction, type AuditResult } from "@/lib/audit";

export const metadata: Metadata = { title: "Auditoría" };

type Filters = { action?: AuditAction; result?: AuditResult; page: number };

function href({ action, result, page }: Filters) {
  const query = new URLSearchParams();
  if (action) query.set("accion", action);
  if (result) query.set("resultado", result);
  if (page > 1) query.set("page", String(page));
  const text = query.toString();
  return text ? `/admin/auditoria?${text}` : "/admin/auditoria";
}

async function AuditTable({ token, filters }: { token: string; filters: Filters }) {
  const locale = await getLocale();
  const result = await listAudit(token, filters);
  if (!result.ok) {
    if (result.status === 503 || result.status === 504) {
      return <ServiceUnavailable reason={result.error.code === "timeout" ? "timeout" : "unavailable"} retryHref={href(filters)} />;
    }
    return (
      <p className="error" role="alert">
        {result.status === 404 ? t(locale, "faq.missingPage") : result.error.message}{" "}
        <Link href="/admin/auditoria">{t(locale, "faq.firstPage")}</Link>
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
        <table className="table" data-testid="audit-table">
          <thead>
            <tr>
              <th>{t(locale, "audit.date")}</th>
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
        {previous && <Link href={href({ ...filters, page: filters.page - 1 })}>{t(locale, "common.previous")}</Link>}
        <span className="muted">
          {t(locale, "common.page")} {filters.page}
        </span>
        {next && <Link href={href({ ...filters, page: filters.page + 1 })}>{t(locale, "common.next")}</Link>}
      </nav>
    </>
  );
}

async function Audit({ searchParams }: { searchParams: PageProps<"/admin/auditoria">["searchParams"] }) {
  const locale = await getLocale();
  const { accion, resultado, page } = await searchParams;
  const filters: Filters = {
    action: AUDIT_ACTIONS.includes(accion as AuditAction) ? (accion as AuditAction) : undefined,
    result: AUDIT_RESULTS.includes(resultado as AuditResult) ? (resultado as AuditResult) : undefined,
    page: Math.max(1, Number.parseInt(String(page ?? "1"), 10) || 1),
  };
  return (
    <RoleGate roles={["admin"]} forbiddenMessage={t(locale, "audit.forbidden")} retryHref="/admin/auditoria">
      {async (token) => (
        <>
          {/* Formulario GET: funciona sin JavaScript y deja los filtros en la URL. */}
          <form method="get" action="/admin/auditoria" className="filters">
            <label>
              {t(locale, "audit.action")}
              <select name="accion" defaultValue={filters.action ?? ""}>
                <option value="">{t(locale, "audit.all")}</option>
                {AUDIT_ACTIONS.map((action) => (
                  <option key={action} value={action}>
                    {t(locale, `audit.action.${action}`)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t(locale, "audit.result")}
              <select name="resultado" defaultValue={filters.result ?? ""}>
                <option value="">{t(locale, "audit.all")}</option>
                {AUDIT_RESULTS.map((value) => (
                  <option key={value} value={value}>
                    {t(locale, `audit.result.${value}`)}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit">{t(locale, "audit.filter")}</button>
          </form>
          <AuditTable token={token} filters={filters} />
        </>
      )}
    </RoleGate>
  );
}

export default async function AuditPage({ searchParams }: PageProps<"/admin/auditoria">) {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "audit.title")}</h1>
      <p className="muted">{t(locale, "audit.intro")}</p>
      <p>
        <Link href="/chat">{t(locale, "common.backChat")}</Link>
      </p>
      <Suspense fallback={<p className="muted">{t(locale, "audit.loading")}</p>}>
        <Audit searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
