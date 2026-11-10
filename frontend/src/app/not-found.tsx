import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import Link from "next/link";

export default async function NotFound() {
  const locale = await getLocale();
  return (
    <main>
      <h1>{t(locale, "notfound.title")}</h1>
      <p className="muted">{t(locale, "notfound.message")}</p>
      <Link href="/">{t(locale, "common.backHome")}</Link>
    </main>
  );
}
