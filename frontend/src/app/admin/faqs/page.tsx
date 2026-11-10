import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { FaqForm } from "@/components/FaqForm";
import { FaqRowActions } from "@/components/FaqRowActions";
import { listFaqs } from "@/lib/faqs";
import { createFaqAction } from "./actions";

export const metadata: Metadata = { title: "Administrar preguntas frecuentes" };

async function FaqTable({ token, page }: { token: string; page: number }) {
  const locale = await getLocale();
  const result = await listFaqs(token, page);
  if (!result.ok) {
    return (
      <p className="error" role="alert">
        {result.status === 404 ? t(locale, "faq.missingPage") : result.error.message}{" "}
        <Link href="/admin/faqs">{t(locale, "faq.firstPage")}</Link>
      </p>
    );
  }
  const { count, next, previous, results } = result.data;
  return (
    <>
      <p className="muted">{t(locale, "faq.total", { count })}</p>
      <div className="table-wrap">
        <table className="table" data-testid="faq-table">
          <thead>
            <tr>
              <th>{t(locale, "common.category")}</th>
              <th>{t(locale, "common.question")}</th>
              <th>{t(locale, "common.status")}</th>
              <th>{t(locale, "common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {results.map((faq) => (
              <tr key={faq.id} data-testid={`faq-row-${faq.id}`}>
                <td>{faq.category}</td>
                <td>{faq.question}</td>
                <td className={faq.is_active ? "ok" : "muted"}>
                  {t(locale, faq.is_active ? "common.active" : "common.inactive")}
                </td>
                <td>
                  <FaqRowActions id={faq.id} question={faq.question} isActive={faq.is_active} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <nav className="links" aria-label="Paginación">
        {previous && <Link href={`/admin/faqs?page=${page - 1}`}>{t(locale, "common.previous")}</Link>}
        <span className="muted">{t(locale, "common.page")} {page}</span>
        {next && <Link href={`/admin/faqs?page=${page + 1}`}>{t(locale, "common.next")}</Link>}
      </nav>
    </>
  );
}

async function Admin({ searchParams }: { searchParams: PageProps<"/admin/faqs">["searchParams"] }) {
  const locale = await getLocale();
  const { page } = await searchParams;
  const pageNumber = Math.max(1, Number.parseInt(String(page ?? "1"), 10) || 1);
  return (
    <RoleGate
      roles={["admin"]}
      forbiddenMessage={t(locale, "faq.forbidden")}
      retryHref="/admin/faqs"
    >
      {async (token) => (
        <>
          <h2>{t(locale, "faq.new")}</h2>
          <FaqForm action={createFaqAction} submitLabel={t(locale, "faq.create")} />
          <h2>{t(locale, "faq.list")}</h2>
          <FaqTable token={token} page={pageNumber} />
        </>
      )}
    </RoleGate>
  );
}

export default async function AdminFaqsPage({ searchParams }: PageProps<"/admin/faqs">) {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "faq.title")}</h1>
      <p className="muted">
        {t(locale, "faq.intro")}
      </p>
      <Suspense fallback={<p className="muted">{t(locale, "common.loading")}</p>}>
        <Admin searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
