import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "En mantenimiento" };

export default function Mantenimiento() {
  return (
    <main>
      <h1>Sitio en mantenimiento</h1>
      <p className="muted">
        Estamos realizando trabajos en el servicio. Vuelve a intentarlo en unos minutos.
      </p>
      <Link href="/">Volver al inicio</Link>
    </main>
  );
}
