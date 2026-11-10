import "server-only";
import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { getSession, type User } from "@/lib/session";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";

/**
 * Muestra el contenido solo a los roles indicados. La API vuelve a comprobar el
 * permiso en cada petición; esta puerta solo evita mostrar una pantalla inútil.
 */
export async function RoleGate({
  roles,
  forbiddenMessage,
  retryHref,
  children,
}: {
  roles: string[];
  forbiddenMessage: string;
  retryHref: string;
  children: (token: string, user: User) => Promise<ReactNode>;
}) {
  const session = await getSession();
  if (session.state === "anonymous") redirect(session.expired ? "/login?motivo=expirada" : "/login");
  if (session.state === "unavailable") {
    return <ServiceUnavailable reason={session.reason} retryHref={retryHref} />;
  }
  // "plataforma" = superadministrador de la plataforma (no depende del negocio elegido).
  const allowed =
    roles.includes(session.user.role) || (roles.includes("plataforma") && session.user.is_platform_admin === true);
  if (!allowed) {
    return (
      <div data-testid="role-forbidden">
        <p className="error" role="alert">
          {forbiddenMessage}
        </p>
        <Link href="/chat">Chat</Link>
      </div>
    );
  }
  return children(session.token, session.user);
}
