"use client";

// Último recurso: falla el layout raíz y no hay proveedor de idioma disponible,
// por eso el texto aparece en los dos idiomas.
export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="es">
      <body>
        <main>
          <h1>Ocurrió un error / An error occurred</h1>
          <p>No pudimos mostrar el sitio. / We couldn&apos;t display the site.</p>
          <button onClick={reset}>Reintentar / Try again</button>
        </main>
      </body>
    </html>
  );
}
