import { t, type Locale } from "@/lib/i18n";

/** Funciona sin JavaScript: POST, cookie y redirección a la página actual. */
export function LocaleSwitcher({ locale }: { locale: Locale }) {
  return (
    <header className="locale-header">
      <form action="/api/idioma" method="post" className="locale-switcher" aria-label={t(locale, "app.language")}>
        <span>{t(locale, "app.language")}</span>
        <button type="submit" name="lang" value="es" aria-pressed={locale === "es"} className="locale-button">
          ES
        </button>
        <button type="submit" name="lang" value="en" aria-pressed={locale === "en"} className="locale-button">
          EN
        </button>
      </form>
    </header>
  );
}
