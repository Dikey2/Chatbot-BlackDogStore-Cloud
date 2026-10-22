import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { listConversations, STATUS_LABELS, type ConversationStatus } from "@/lib/chat";

export const metadata: Metadata = { title: "Bandeja del asesor" };

const STATUSES = Object.keys(STATUS_LABELS) as ConversationStatus[];
const dateFormat = new Intl.DateTimeFormat("es-PE", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Lima",
});

async function Inbox({ token, status, page }: { token: string; status: ConversationStatus; page: number }) {
  const result = await listConversations(token, status, page);
  if (!result.ok) {
    return (
      <p className="error" role="alert">
        {result.status === 404 ? "Esa página no existe." : result.error.message}{" "}
        <Link href={`/asesor?estado=${status}`}>Volver a la primera página</Link>
      </p>
    );
  }
  const { count, next, previous, results } = result.data;
  if (count === 0) return <p className="muted">No hay conversaciones en este estado.</p>;
  return (
    <>
      <div className="table-wrap">
        <table className="table" data-testid="inbox-table">
          <thead>
            <tr>
              <th>N.º</th>
              <th>Cliente</th>
              <th>Inicio</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {results.map((conversation) => (
              <tr key={conversation.id}>
                <td>{conversation.id}</td>
                <td>{conversation.user_name}</td>
                <td>{dateFormat.format(new Date(conversation.created_at))}</td>
                <td>
                  <Link href={`/asesor/${conversation.id}`}>Ver conversación</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <nav className="links" aria-label="Paginación">
        {previous && <Link href={`/asesor?estado=${status}&page=${page - 1}`}>Anterior</Link>}
        <span className="muted">
          Página {page} · {count} en total
        </span>
        {next && <Link href={`/asesor?estado=${status}&page=${page + 1}`}>Siguiente</Link>}
      </nav>
    </>
  );
}

async function AdvisorInbox({ searchParams }: { searchParams: PageProps<"/asesor">["searchParams"] }) {
  const { estado, page } = await searchParams;
  const status = STATUSES.includes(estado as ConversationStatus) ? (estado as ConversationStatus) : "derivada";
  const pageNumber = Math.max(1, Number.parseInt(String(page ?? "1"), 10) || 1);
  return (
    <RoleGate
      roles={["asesor", "admin"]}
      forbiddenMessage="No tienes permiso para ver la bandeja del asesor."
      retryHref="/asesor"
    >
      {async (token) => (
        <>
          <nav className="tabs" aria-label="Estado">
            {STATUSES.map((value) => (
              <Link key={value} href={`/asesor?estado=${value}`} aria-current={value === status ? "page" : undefined}>
                {STATUS_LABELS[value]}
              </Link>
            ))}
          </nav>
          <Inbox token={token} status={status} page={pageNumber} />
        </>
      )}
    </RoleGate>
  );
}

export default function AdvisorPage({ searchParams }: PageProps<"/asesor">) {
  return (
    <main className="wide">
      <h1>Bandeja del asesor</h1>
      <p className="muted">
        Las conversaciones derivadas son consultas que el chatbot no pudo responder.
      </p>
      <p>
        <Link href="/chat">Volver al chat</Link>
      </p>
      <Suspense fallback={<p className="muted">Cargando conversaciones…</p>}>
        <AdvisorInbox searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
