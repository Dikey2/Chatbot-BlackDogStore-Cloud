import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { logoutAction } from "@/app/actions";
import { ChatBox } from "@/components/ChatBox";
import { getLatestConversation } from "@/lib/chat";
import { getSession, loginPath } from "@/lib/session";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";

export const metadata: Metadata = { title: "Chat" };

async function ConnectionError({ message }: { message: string }) {
  const locale = await getLocale();
  return (
    <div data-testid="chat-unavailable">
      <p className="error" role="alert">
        {message}
      </p>
      <Link href="/chat">{t(locale, "common.retry")}</Link>
    </div>
  );
}

async function Chat() {
  const locale = await getLocale();
  const session = await getSession();
  if (session.state === "anonymous") redirect(session.expired ? "/login?motivo=expirada" : "/login");
  if (session.state === "unavailable") {
    return <ServiceUnavailable reason={session.reason} retryHref="/chat" />;
  }

  const history = await getLatestConversation(session.token);
  if (!history.ok && history.status === 401) redirect(loginPath(history.error));

  return (
    <>
      <form action={logoutAction} className="session">
        <span data-testid="session-user">
          {session.user.name} ({session.user.role})
        </span>
        {session.user.role !== "cliente" && <Link href="/asesor">{t(locale, "home.advisor")}</Link>}
        {session.user.role === "admin" && <Link href="/admin/faqs">{t(locale, "home.faq")}</Link>}
        {session.user.role === "admin" && <Link href="/admin/auditoria">{t(locale, "home.audit")}</Link>}
        <button type="submit">{t(locale, "chat.logout")}</button>
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
        <ConnectionError message={t(locale, "chat.historyUnavailable")} />
      )}
    </>
  );
}

export default async function ChatPage() {
  const locale = await getLocale();
  return (
    <main>
      <h1>{t(locale, "chat.title")}</h1>
      <Suspense
        fallback={
          <p className="muted" data-testid="history-loading">
            {t(locale, "chat.loadingHistory")}
          </p>
        }
      >
        <Chat />
      </Suspense>
    </main>
  );
}
