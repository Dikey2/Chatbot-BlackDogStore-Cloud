import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { loginAction } from "@/app/actions";
import { AuthForm } from "@/components/AuthForm";

export const metadata: Metadata = { title: "Iniciar sesión" };

async function ExpiredNotice({ searchParams }: { searchParams: PageProps<"/login">["searchParams"] }) {
  const { motivo } = await searchParams;
  const locale = await getLocale();
  if (motivo !== "expirada") return null;
  return (
    <p className="error" role="status" data-testid="session-expired">
      {t(locale, "login.expired")}
    </p>
  );
}

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const locale = await getLocale();
  return (
    <main>
      <h1>{t(locale, "login.title")}</h1>
      <Suspense>
        <ExpiredNotice searchParams={searchParams} />
      </Suspense>
      <AuthForm
        action={loginAction}
        submitLabel={t(locale, "login.submit")}
        fields={[
          { name: "email", label: t(locale, "common.email"), type: "email", autoComplete: "email" },
          {
            name: "password",
            label: t(locale, "common.password"),
            type: "password",
            autoComplete: "current-password",
          },
        ]}
      />
      <p>
        {t(locale, "login.noAccount")} <Link href="/registro">{t(locale, "login.register")}</Link>
      </p>
    </main>
  );
}
