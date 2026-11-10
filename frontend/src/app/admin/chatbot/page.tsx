import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { PanelNav } from "@/components/PanelNav";
import { ActionButton, ChatbotConfigForm, DomainForm, InstallSnippet } from "@/components/PanelForms";
import { API_PUBLIC_URL } from "@/lib/api";
import { getBusiness, listDomains } from "@/lib/business";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import { addDomainAction, deleteDomainAction, updateBusinessAction } from "@/app/panel/actions";

export const metadata: Metadata = { title: "Configuración del chatbot" };

async function Settings({ token }: { token: string }) {
  const locale = await getLocale();
  const [business, domains] = await Promise.all([getBusiness(token), listDomains(token)]);
  if (!business.ok) {
    return (
      <p className="error" role="alert">
        {business.error.message}
      </p>
    );
  }
  const b = business.data;
  const c = b.chatbot;
  const snippet = `<script\n  src="${API_PUBLIC_URL}/widget.js"\n  data-chatbot-id="${b.public_id}"\n  defer>\n</script>`;
  return (
    <>
      <h2>{t(locale, "panel.install")}</h2>
      <p className="muted">{t(locale, "panel.installHelp")}</p>
      <InstallSnippet code={snippet} />
      <p>
        <Link href={`/vista-previa?id=${encodeURIComponent(b.public_id)}`} target="_blank" data-testid="preview-link">
          {t(locale, "panel.preview")}
        </Link>
      </p>

      <h2>{t(locale, "panel.domains")}</h2>
      <p className="muted">{t(locale, "panel.domainsHelp")}</p>
      {domains.ok && domains.data.length > 0 ? (
        <ul className="status" data-testid="domain-list">
          {domains.data.map((domain) => (
            <li key={domain.id}>
              <code>{domain.origin}</code>
              <ActionButton
                action={deleteDomainAction.bind(null, domain.id)}
                label={t(locale, "panel.remove")}
                confirmText={t(locale, "panel.removeDomainConfirm", { origin: domain.origin })}
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">{t(locale, "panel.noDomains")}</p>
      )}
      <DomainForm action={addDomainAction} />

      <h2>{t(locale, "panel.chatbot")}</h2>
      <ChatbotConfigForm
        action={updateBusinessAction}
        initial={{
          name: b.name,
          description: b.description,
          logo_url: b.logo_url,
          assistant_name: c?.assistant_name ?? "",
          welcome_message: c?.welcome_message ?? "",
          no_answer_message: c?.no_answer_message ?? "",
          handoff_message: c?.handoff_message ?? "",
          handoff_keywords: c?.handoff_keywords ?? "",
          schedule: c?.schedule ?? "",
          contact_info: c?.contact_info ?? "",
          primary_color: c?.primary_color ?? "#111111",
          is_active: c?.is_active ?? true,
        }}
      />
    </>
  );
}

async function Content() {
  const locale = await getLocale();
  return (
    <RoleGate roles={["admin"]} forbiddenMessage={t(locale, "panel.adminOnly")} retryHref="/admin/chatbot">
      {async (token, user) => (
        <>
          <PanelNav user={user} current="/admin/chatbot" />
          <Settings token={token} />
        </>
      )}
    </RoleGate>
  );
}

export default async function ChatbotSettingsPage() {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "panel.chatbotTitle")}</h1>
      <Suspense fallback={<p className="muted">{t(locale, "common.loading")}</p>}>
        <Content />
      </Suspense>
    </main>
  );
}
