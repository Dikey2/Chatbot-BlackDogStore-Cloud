"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <main>
      <h1>Ocurrió un error</h1>
      <p className="muted">No pudimos mostrar esta página. Inténtalo otra vez.</p>
      <button onClick={reset}>Reintentar</button>
    </main>
  );
}
