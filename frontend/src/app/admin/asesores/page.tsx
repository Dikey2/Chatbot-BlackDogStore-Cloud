import type { Metadata } from "next";
import { Suspense } from "react";
import { RoleGate } from "@/components/RoleGate";
import { PanelNav } from "@/components/PanelNav";
import { ActionButton, MemberForm } from "@/components/PanelForms";
import { listMembers } from "@/lib/business";
import { t } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import { addMemberAction, removeMemberAction } from "@/app/panel/actions";

export const metadata: Metadata = { title: "Equipo del negocio" };

async function Team({ token, userId }: { token: string; userId: number }) {
  const locale = await getLocale();
  const result = await listMembers(token);
  if (!result.ok) {
    return (
      <p className="error" role="alert">
        {result.error.message}
      </p>
    );
  }
  return (
    <>
      <div className="table-wrap">
        <table className="table" data-testid="member-table">
          <thead>
            <tr>
              <th>{t(locale, "common.name")}</th>
              <th>{t(locale, "common.email")}</th>
              <th>{t(locale, "panel.role")}</th>
              <th>{t(locale, "common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {result.data.map((member) => (
              <tr key={member.id}>
                <td>{member.name}</td>
                <td>{member.email}</td>
                <td>{member.role === "admin" ? t(locale, "panel.roleAdmin") : t(locale, "common.advisor")}</td>
                <td>
                  {member.user !== userId && (
                    <ActionButton
                      action={removeMemberAction.bind(null, member.id)}
                      label={t(locale, "panel.remove")}
                      confirmText={t(locale, "panel.removeMemberConfirm", { email: member.email })}
                    />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h2>{t(locale, "panel.addMember")}</h2>
      <p className="muted">{t(locale, "panel.addMemberHelp")}</p>
      <MemberForm action={addMemberAction} />
    </>
  );
}

async function Content() {
  const locale = await getLocale();
  return (
    <RoleGate roles={["admin"]} forbiddenMessage={t(locale, "panel.adminOnly")} retryHref="/admin/asesores">
      {async (token, user) => (
        <>
          <PanelNav user={user} current="/admin/asesores" />
          <Team token={token} userId={user.id} />
        </>
      )}
    </RoleGate>
  );
}

export default async function TeamPage() {
  const locale = await getLocale();
  return (
    <main className="wide">
      <h1>{t(locale, "panel.teamTitle")}</h1>
      <Suspense fallback={<p className="muted">{t(locale, "common.loading")}</p>}>
        <Content />
      </Suspense>
    </main>
  );
}
