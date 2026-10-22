import Link from "next/link";

export default function NotFound() {
  return (
    <main>
      <h1>404: página no encontrada</h1>
      <p className="muted">La dirección que buscas no existe.</p>
      <Link href="/">Volver al inicio</Link>
    </main>
  );
}
