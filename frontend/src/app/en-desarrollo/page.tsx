import Link from "next/link";

export default function EnDesarrollo() {
  return (
    <main>
      <h1>Sección en desarrollo</h1>
      <p className="muted">Esta parte del prototipo todavía no está disponible.</p>
      <Link href="/">Volver al inicio</Link>
    </main>
  );
}
