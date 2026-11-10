import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { FaqForm } from "@/components/FaqForm";
import { getFaq } from "@/lib/faqs";
import { updateFaqAction } from "../actions";

export const metadata: Metadata = { title: "Editar pregunta frecuente" };

async function EditForm({ token, id }: { token: string; id: number }) {
  const locale = await getLocale();
  const result = await getFaq(token, id);
  if (!result.ok) {
    if (result.status === 404) notFound();
    return (
      <p className="error" role="alert">
        {result.error.message}
      </p>
    );
  }
  const faq = result.data;
  return (
    <FaqForm
      action={updateFaqAction.bind(null, faq.id)}
      initial={faq}
      submitLabel={t(locale, "faq.save")}
    />
  );
}

async function Edit({ params }: { params: PageProps<"/admin/faqs/[id]">["params"] }) {
  const locale = await getLocale();
  const id = Number.parseInt((await params).id, 10);
  if (!Number.isInteger(id) || id < 1) notFound();
  return <RoleGate
      roles={["admin"]}
      forbiddenMessage={t(locale, "faq.forbidden")}
      retryHref="/admin/faqs"
    >{async (token) => <EditForm token={token} id={id} />}</RoleGate>;
}

export default async function EditFaqPage({ params }: PageProps<"/admin/faqs/[id]">) {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "faq.editTitle")}</h1>
      <p>
        <Link href="/admin/faqs">{t(locale, "faq.backList")}</Link>
      </p>
      <Suspense fallback={<p className="muted">{t(locale, "common.loading")}</p>}>
        <Edit params={params} />
      </Suspense>
    </main>
  );
}
