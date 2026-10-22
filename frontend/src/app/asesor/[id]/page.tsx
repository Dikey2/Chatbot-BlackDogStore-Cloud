import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { AdvisorReply } from "@/components/AdvisorReply";
import { RoleGate } from "@/components/RoleGate";
import { getConversation, SENDER_LABELS, STATUS_LABELS } from "@/lib/chat";
import { replyAction } from "../actions";

export const metadata: Metadata = { title: "Conversación" };

async function ConversationView({ token, id }: { token: string; id: number }) {
  const result = await getConversation(token, id);
  if (!result.ok) {
    if (result.status === 404) notFound();
    return (
      <p className="error" role="alert">
        {result.error.message}
      </p>
    );
  }
  const conversation = result.data;
  return (
    <>
      <p>
        Cliente: <strong>{conversation.user_name}</strong> · Estado:{" "}
        <span data-testid="conversation-status">{conversation.status}</span>
      </p>
      <ol className="messages" data-testid="messages">
        {conversation.messages.map((message) => (
          <li key={message.id} className={`message ${message.sender}`} data-sender={message.sender}>
            <span className="sender">{SENDER_LABELS[message.sender]}</span>
            {message.content}
          </li>
        ))}
      </ol>
      {conversation.status === "cerrada" ? (
        <p className="muted" data-testid="conversation-closed">
          Conversación cerrada.
        </p>
      ) : (
        <AdvisorReply conversationId={conversation.id} action={replyAction.bind(null, conversation.id)} />
      )}
      <p>
        <Link href={`/asesor?estado=${conversation.status}`}>
          Volver a {STATUS_LABELS[conversation.status].toLowerCase()}
        </Link>
      </p>
    </>
  );
}

async function Detail({ params }: { params: PageProps<"/asesor/[id]">["params"] }) {
  const id = Number.parseInt((await params).id, 10);
  if (!Number.isInteger(id) || id < 1) notFound();
  return (
    <RoleGate
      roles={["asesor", "admin"]}
      forbiddenMessage="No tienes permiso para ver conversaciones de clientes."
      retryHref={`/asesor/${id}`}
    >
      {async (token) => <ConversationView token={token} id={id} />}
    </RoleGate>
  );
}

export default function ConversationPage({ params }: PageProps<"/asesor/[id]">) {
  return (
    <main className="wide">
      <h1>Conversación</h1>
      <Suspense fallback={<p className="muted">Cargando conversación…</p>}>
        <Detail params={params} />
      </Suspense>
    </main>
  );
}
