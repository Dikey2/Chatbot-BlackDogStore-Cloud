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
  // El estado se consulta en cada petición, no al compilar.
  await connection();
  const health = await getHealth();
  return (
    <ul className="status">
      {(Object.keys(LABELS) as (keyof typeof LABELS)[]).map((key) => (
        <li key={key}>
          <span>{LABELS[key]}</span>
          <span className={health[key]} data-testid={`status-${key}`}>
            {health[key] === "ok" ? "Operativo" : "Sin respuesta"}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function Home() {
  return (
    <main>
      <h1>Chatbot Black Dog Store</h1>
      <p className="muted">
        Prototipo académico. No está conectado a la tienda real y usa datos
        ficticios.
      </p>
      <h2>Estado de los servicios</h2>
      <Suspense fallback={<p className="muted">Consultando servicios…</p>}>
        <ServiceStatus />
      </Suspense>
      <nav className="links">
        <Link href="/chat">Chat</Link>
        <Link href="/login">Iniciar sesión</Link>
        <Link href="/registro">Crear cuenta</Link>
        <Link href="/admin/faqs">Administrar FAQ</Link>
        <Link href="/asesor">Bandeja del asesor</Link>
        <Link href="/en-desarrollo">Catálogo de productos (en desarrollo)</Link>
      </nav>
    </main>
  );
}
