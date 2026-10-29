import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
import { registerAction } from "@/app/actions";
import { AuthForm } from "@/components/AuthForm";

export const metadata: Metadata = { title: "Crear cuenta" };

export default async function RegisterPage() {
  const locale = await getLocale();
  return (
    <main>
      <h1>{t(locale, "register.title")}</h1>
      <p className="muted">
        {t(locale, "register.disclaimer")}
      </p>
      <AuthForm
        action={registerAction}
        submitLabel={t(locale, "register.submit")}
        fields={[
          { name: "name", label: t(locale, "common.name"), type: "text", autoComplete: "name" },
          { name: "email", label: t(locale, "common.email"), type: "email", autoComplete: "email" },
          {
            name: "password",
            label: t(locale, "common.passwordMin"),
            type: "password",
            autoComplete: "new-password",
          },
        ]}
      />
      <p>
        {t(locale, "register.hasAccount")} <Link href="/login">{t(locale, "register.login")}</Link>
      </p>
    </main>
  );
}
