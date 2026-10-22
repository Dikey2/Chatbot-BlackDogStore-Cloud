import type { Metadata } from "next";
import Link from "next/link";
import { registerAction } from "@/app/actions";
import { AuthForm } from "@/components/AuthForm";

export const metadata: Metadata = { title: "Crear cuenta" };

export default function RegisterPage() {
  return (
    <main>
      <h1>Crear cuenta</h1>
      <p className="muted">
        Prototipo académico: usa datos ficticios, no tu contraseña real.
      </p>
      <AuthForm
        action={registerAction}
        submitLabel="Registrarme"
        fields={[
          { name: "name", label: "Nombre", type: "text", autoComplete: "name" },
          { name: "email", label: "Correo", type: "email", autoComplete: "email" },
          {
            name: "password",
            label: "Contraseña (mínimo 8 caracteres)",
            type: "password",
            autoComplete: "new-password",
          },
        ]}
      />
      <p>
        ¿Ya tienes cuenta? <Link href="/login">Inicia sesión</Link>
      </p>
    </main>
  );
}
