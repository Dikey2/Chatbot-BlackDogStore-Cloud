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
  const result = await listFaqs(token, page);
  if (!result.ok) {
    return (
      <p className="error" role="alert">
        {result.status === 404 ? "Esa página no existe." : result.error.message}{" "}
        <Link href="/admin/faqs">Volver a la primera página</Link>
      </p>
    );
  }
  const { count, next, previous, results } = result.data;
  return (
    <>
      <p className="muted">{count} preguntas frecuentes en total.</p>
      <div className="table-wrap">
        <table className="table" data-testid="faq-table">
          <thead>
            <tr>
              <th>Categoría</th>
              <th>Pregunta</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {results.map((faq) => (
              <tr key={faq.id} data-testid={`faq-row-${faq.id}`}>
                <td>{faq.category}</td>
                <td>{faq.question}</td>
                <td className={faq.is_active ? "ok" : "muted"}>
                  {faq.is_active ? "Activa" : "Inactiva"}
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
        {previous && <Link href={`/admin/faqs?page=${page - 1}`}>Anterior</Link>}
        <span className="muted">Página {page}</span>
        {next && <Link href={`/admin/faqs?page=${page + 1}`}>Siguiente</Link>}
      </nav>
    </>
  );
}

async function Admin({ searchParams }: { searchParams: PageProps<"/admin/faqs">["searchParams"] }) {
  const { page } = await searchParams;
  const pageNumber = Math.max(1, Number.parseInt(String(page ?? "1"), 10) || 1);
  return (
    <RoleGate
      roles={["admin"]}
      forbiddenMessage="No tienes permiso para administrar las preguntas frecuentes."
      retryHref="/admin/faqs"
    >
      {async (token) => (
        <>
          <h2>Nueva pregunta frecuente</h2>
          <FaqForm action={createFaqAction} submitLabel="Crear" />
          <h2>Preguntas registradas</h2>
          <FaqTable token={token} page={pageNumber} />
        </>
      )}
    </RoleGate>
  );
}

export default function AdminFaqsPage({ searchParams }: PageProps<"/admin/faqs">) {
  return (
    <main className="wide">
      <h1>Administrar preguntas frecuentes</h1>
      <p className="muted">
        Las preguntas activas las usa el chatbot para responder. Solo datos ficticios.
      </p>
      <Suspense fallback={<p className="muted">Cargando…</p>}>
        <Admin searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
