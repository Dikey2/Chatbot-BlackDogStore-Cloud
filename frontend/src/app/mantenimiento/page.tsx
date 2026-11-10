import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "En mantenimiento" };

export default async function Mantenimiento() {
  const locale = await getLocale();
  return (
    <main>
      <h1>{t(locale, "maintenance.title")}</h1>
      <p className="muted">
        {t(locale, "maintenance.message")}
      </p>
      <Link href="/">{t(locale, "common.backHome")}</Link>
    </main>
  );
}
