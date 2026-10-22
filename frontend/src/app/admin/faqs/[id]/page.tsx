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
      submitLabel="Guardar cambios"
    />
  );
}

async function Edit({ params }: { params: PageProps<"/admin/faqs/[id]">["params"] }) {
  const id = Number.parseInt((await params).id, 10);
  if (!Number.isInteger(id) || id < 1) notFound();
  return <RoleGate
      roles={["admin"]}
      forbiddenMessage="No tienes permiso para administrar las preguntas frecuentes."
      retryHref="/admin/faqs"
    >{async (token) => <EditForm token={token} id={id} />}</RoleGate>;
}

export default function EditFaqPage({ params }: PageProps<"/admin/faqs/[id]">) {
  return (
    <main className="wide">
      <h1>Editar pregunta frecuente</h1>
      <p>
        <Link href="/admin/faqs">Volver al listado</Link>
      </p>
      <Suspense fallback={<p className="muted">Cargando…</p>}>
        <Edit params={params} />
      </Suspense>
    </main>
  );
}
