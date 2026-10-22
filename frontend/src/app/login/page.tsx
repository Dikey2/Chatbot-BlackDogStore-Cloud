import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { loginAction } from "@/app/actions";
import { AuthForm } from "@/components/AuthForm";

export const metadata: Metadata = { title: "Iniciar sesión" };

async function ExpiredNotice({ searchParams }: { searchParams: PageProps<"/login">["searchParams"] }) {
  const { motivo } = await searchParams;
  if (motivo !== "expirada") return null;
  return (
    <p className="error" role="status" data-testid="session-expired">
      Tu sesión expiró. Inicia sesión de nuevo.
    </p>
  );
}

export default function LoginPage({ searchParams }: PageProps<"/login">) {
  return (
    <main>
      <h1>Iniciar sesión</h1>
      <Suspense>
        <ExpiredNotice searchParams={searchParams} />
      </Suspense>
      <AuthForm
        action={loginAction}
        submitLabel="Entrar"
        fields={[
          { name: "email", label: "Correo", type: "email", autoComplete: "email" },
          {
            name: "password",
            label: "Contraseña",
            type: "password",
            autoComplete: "current-password",
          },
        ]}
      />
      <p>
        ¿No tienes cuenta? <Link href="/registro">Regístrate</Link>
      </p>
    </main>
  );
}
