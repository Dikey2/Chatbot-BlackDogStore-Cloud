import type { Metadata } from "next";
import Link from "next/link";
import { loginAction } from "@/app/actions";
import { AuthForm } from "@/components/AuthForm";

export const metadata: Metadata = { title: "Iniciar sesión" };

export default function LoginPage() {
  return (
    <main>
      <h1>Iniciar sesión</h1>
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
