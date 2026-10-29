
import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { getHealth } from "@/lib/api";

const LABELS = {
  backend: "API Django",
  database: "PostgreSQL",
  chatbot: "Servicio de chatbot",
} as const;

async function ServiceStatus() {
  const locale = await getLocale();

  // Consultar el estado de los servicios en cada petición.
  await connection();
  const health = await getHealth();

  return (
    <ul className="status">
      {(Object.keys(LABELS) as (keyof typeof LABELS)[]).map((key) => (
        <li key={key}>
          <span>
            {key === "chatbot"
              ? t(locale, "home.chatbot")
              : LABELS[key]}
          </span>
          <span
            className={health[key]}
            data-testid={`status-${key}`}
          >
            {t(locale, health[key] === "ok" ? "home.ok" : "home.error")}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default async function Home() {
  const locale = await getLocale();

  return (
    <main>
      <h1>Chatbot Black Dog Store</h1>
      <p className="muted">{t(locale, "home.description")}</p>

      <h2>{t(locale, "home.services")}</h2>

      <Suspense
        fallback={
          <p className="muted">
            {t(locale, "home.checking")}
          </p>
        }
      >
        <ServiceStatus />
      </Suspense>

      <nav className="links">
        <Link href="/chat">Chat</Link>
        <Link href="/login">
          {t(locale, "home.login")}
        </Link>
        <Link href="/registro">
          {t(locale, "home.register")}
        </Link>
        <Link href="/admin/faqs">
          {t(locale, "home.faq")}
        </Link>
        <Link href="/asesor">
          {t(locale, "home.advisor")}
        </Link>
        <Link href="/admin/auditoria">
          {t(locale, "home.audit")}
        </Link>
        <Link href="/en-desarrollo">
          {t(locale, "home.catalog")}
        </Link>
      </nav>
    </main>
  );
}
