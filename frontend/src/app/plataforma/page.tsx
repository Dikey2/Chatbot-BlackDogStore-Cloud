import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { PanelNav } from "@/components/PanelNav";
import { ActionButton, BusinessCreateForm, MemberForm } from "@/components/PanelForms";
import { getPlatformMetrics, listPlatformBusinesses } from "@/lib/business";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import {
  addBusinessAdminAction,
  createBusinessAction,
  selectBusinessAction,
  setBusinessStateAction,
} from "@/app/panel/actions";

export const metadata: Metadata = { title: "Plataforma" };

async function Platform({ token, page }: { token: string; page: number }) {
  const locale = await getLocale();
  const [metrics, businesses] = await Promise.all([getPlatformMetrics(token), listPlatformBusinesses(token, page)]);
  if (!businesses.ok) {
    return (
      <p className="error" role="alert">
        {businesses.error.message}
      </p>
    );
  }
  return (
    <>
      {metrics.ok && (
        <ul className="metrics" data-testid="platform-metrics">
          {(
            [
              [t(locale, "platform.businesses"), metrics.data.businesses_total ?? 0],
              [t(locale, "platform.active"), metrics.data.businesses_active ?? 0],
              [t(locale, "panel.metric.conversations"), metrics.data.conversations_total],
              [t(locale, "panel.metric.messages"), metrics.data.messages_total],
              [t(locale, "platform.sessions"), metrics.data.visitor_sessions_24h ?? 0],
            ] as [string, number][]
          ).map(([label, value]) => (
            <li key={label}>
              <strong>{value}</strong>
              <span className="muted">{label}</span>
            </li>
          ))}
        </ul>
      )}

      <h2>{t(locale, "platform.list")}</h2>
      <div className="table-wrap">
        <table className="table" data-testid="business-table">
          <thead>
            <tr>
              <th>{t(locale, "common.name")}</th>
              <th>{t(locale, "platform.publicId")}</th>
              <th>{t(locale, "platform.admins")}</th>
              <th>FAQ / {t(locale, "panel.metric.conversations")}</th>
              <th>{t(locale, "common.status")}</th>
              <th>{t(locale, "common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {businesses.data.results.map((b) => (
              <tr key={b.id} data-testid={`business-row-${b.slug}`}>
                <td>
                  <strong>{b.name}</strong>
                  <br />
                  <span className="muted">{b.slug}</span>
                </td>
                <td>
                  <code>{b.public_id}</code>
                </td>
                <td>{b.admins.map((a) => a.email).join(", ") || <span className="muted">—</span>}</td>
                <td>
                  {b.counts.faqs ?? 0} / {b.counts.conversations ?? 0}
                </td>
                <td className={b.is_active ? "ok" : "error"}>
                  {b.is_active ? t(locale, "platform.activeOne") : t(locale, "platform.suspended")}
                </td>
                <td className="cell-actions">
                  <form action={selectBusinessAction}>
                    <input type="hidden" name="business" value={b.id} />
                    <input type="hidden" name="next" value="/panel" />
                    <button type="submit" className="secondary">
                      {t(locale, "platform.manage")}
                    </button>
                  </form>
                  <ActionButton
                    action={setBusinessStateAction.bind(null, b.id, !b.is_active)}
                    label={b.is_active ? t(locale, "platform.suspend") : t(locale, "platform.activate")}
                    confirmText={b.is_active ? t(locale, "platform.suspendConfirm", { name: b.name }) : undefined}
                    testId={`state-${b.slug}`}
                  />
                  <details>
                    <summary>{t(locale, "platform.addAdmin")}</summary>
                    <MemberForm action={addBusinessAdminAction.bind(null, b.id)} allowAdmin={false} />
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <nav className="links" aria-label="Paginación">
        {businesses.data.previous && <Link href={`/plataforma?page=${page - 1}`}>{t(locale, "common.previous")}</Link>}
        <span className="muted">
          {t(locale, "common.page")} {page}
        </span>
        {businesses.data.next && <Link href={`/plataforma?page=${page + 1}`}>{t(locale, "common.next")}</Link>}
      </nav>

      <h2>{t(locale, "platform.new")}</h2>
      <BusinessCreateForm action={createBusinessAction} />
    </>
  );
}

async function Content({ searchParams }: { searchParams: PageProps<"/plataforma">["searchParams"] }) {
  const locale = await getLocale();
  const { page } = await searchParams;
  const pageNumber = Math.max(1, Number.parseInt(String(page ?? "1"), 10) || 1);
  return (
    <RoleGate roles={["plataforma"]} forbiddenMessage={t(locale, "platform.forbidden")} retryHref="/plataforma">
      {async (token, user) => (
        <>
          <PanelNav user={user} current="/plataforma" />
          <Platform token={token} page={pageNumber} />
        </>
      )}
    </RoleGate>
  );
}

export default async function PlatformPage({ searchParams }: PageProps<"/plataforma">) {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "platform.title")}</h1>
      <p className="muted">{t(locale, "platform.intro")}</p>
      <Suspense fallback={<p className="muted">{t(locale, "common.loading")}</p>}>
        <Content searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
