import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { AdvisorReply } from "@/components/AdvisorReply";
import { RoleGate } from "@/components/RoleGate";
import { getConversation } from "@/lib/chat";
import { replyAction } from "../actions";

export const metadata: Metadata = { title: "Conversación" };

async function ConversationView({ token, id }: { token: string; id: number }) {
  const locale = await getLocale();
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
        {t(locale, "common.client")}: <strong>{conversation.user_name}</strong> · {t(locale, "common.status")}: {" "}
        <span data-testid="conversation-status">{conversation.status}</span>
      </p>
      <ol className="messages" data-testid="messages">
        {conversation.messages.map((message) => (
          <li key={message.id} className={`message ${message.sender}`} data-sender={message.sender}>
            <span className="sender">{message.sender === "cliente" ? t(locale, "common.client") : message.sender === "asesor" ? t(locale, "common.advisor") : "Chatbot"}</span>
            {message.content}
          </li>
        ))}
      </ol>
      {conversation.status === "cerrada" ? (
        <p className="muted" data-testid="conversation-closed">
          {t(locale, "advisor.detailClosed")}
        </p>
      ) : (
        <AdvisorReply conversationId={conversation.id} action={replyAction.bind(null, conversation.id)} />
      )}
      <p>
        <Link href={`/asesor?estado=${conversation.status}`}>
          {t(locale, "advisor.backTo", { status: t(locale, conversation.status === "derivada" ? "advisor.escalated" : conversation.status === "abierta" ? "advisor.open" : "advisor.closed").toLowerCase() })}
        </Link>
      </p>
    </>
  );
}

async function Detail({ params }: { params: PageProps<"/asesor/[id]">["params"] }) {
  const locale = await getLocale();
  const id = Number.parseInt((await params).id, 10);
  if (!Number.isInteger(id) || id < 1) notFound();
  return (
    <RoleGate
      roles={["asesor", "admin"]}
      forbiddenMessage={t(locale, "advisor.detailForbidden")}
      retryHref={`/asesor/${id}`}
    >
      {async (token) => <ConversationView token={token} id={id} />}
    </RoleGate>
  );
}

export default async function ConversationPage({ params }: PageProps<"/asesor/[id]">) {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "advisor.detail")}</h1>
      <Suspense fallback={<p className="muted">{t(locale, "advisor.detailLoading")}</p>}>
        <Detail params={params} />
      </Suspense>
    </main>
  );
}
