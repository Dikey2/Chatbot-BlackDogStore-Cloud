import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import Link from "next/link";

export default async function EnDesarrollo() {
  const locale = await getLocale();
  return (
    <main>
      <h1>{t(locale, "inprogress.title")}</h1>
      <p className="muted">{t(locale, "inprogress.message")}</p>
      <Link href="/">{t(locale, "common.backHome")}</Link>
    </main>
  );
}
