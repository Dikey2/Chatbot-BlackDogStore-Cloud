import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { logoutAction } from "@/app/actions";
import { ChatBox } from "@/components/ChatBox";
import { getLatestConversation } from "@/lib/chat";
import { getSession, loginPath } from "@/lib/session";

export const metadata: Metadata = { title: "Chat" };

function ConnectionError({ message }: { message: string }) {
  return (
    <div data-testid="chat-unavailable">
      <p className="error" role="alert">
        {message}
      </p>
      <Link href="/chat">Reintentar</Link>
    </div>
  );
}

async function Chat() {
  const session = await getSession();
  if (session.state === "anonymous") redirect(session.expired ? "/login?motivo=expirada" : "/login");
  if (session.state === "unavailable") {
    return <ConnectionError message="No se pudo conectar con el servidor. Tu sesión sigue activa." />;
  }

  const history = await getLatestConversation(session.token);
  if (!history.ok && history.status === 401) redirect(loginPath(history.error));

  return (
    <>
      <form action={logoutAction} className="session">
        <span data-testid="session-user">
          {session.user.name} ({session.user.role})
        </span>
        {session.user.role !== "cliente" && <Link href="/asesor">Bandeja del asesor</Link>}
        {session.user.role === "admin" && <Link href="/admin/faqs">Administrar FAQ</Link>}
        <button type="submit">Cerrar sesión</button>
      </form>
      {history.ok ? (
        <ChatBox
          initialConversationId={history.data?.id ?? null}
          initialMessages={history.data?.messages ?? []}
          initialEscalated={history.data?.status === "derivada"}
          initialClosed={history.data?.status === "cerrada"}
        />
      ) : (
        // Sin historial no se muestra el chat: un mensaje nuevo abriría otra conversación.
        <ConnectionError message="No se pudo cargar el historial de la conversación." />
      )}
    </>
  );
}

export default function ChatPage() {
  return (
    <main>
      <h1>Chat de atención</h1>
      <Suspense
        fallback={
          <p className="muted" data-testid="history-loading">
            Cargando historial…
          </p>
        }
      >
        <Chat />
      </Suspense>
    </main>
  );
}
