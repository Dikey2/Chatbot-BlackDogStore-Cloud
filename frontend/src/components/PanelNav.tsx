import "server-only";
import Link from "next/link";
import { getLocale } from "@/lib/locale";
import { t } from "@/lib/i18n";
import type { User } from "@/lib/session";
import { selectBusinessAction } from "@/app/panel/actions";

/**
 * Navegación del panel y selector de negocio. El selector solo aparece si el
 * usuario pertenece a más de un negocio (o es superadministrador). Elegir un
 * negocio guarda una cookie; Django vuelve a comprobar la membresía en cada petición.
 */
export async function PanelNav({ user, current }: { user: User; current: string }) {
  const locale = await getLocale();
  const memberships = user.memberships ?? [];
  const isAdmin = user.role === "admin";
  const links = [
    { href: "/panel", label: t(locale, "panel.title"), show: true },
    { href: "/asesor", label: t(locale, "home.advisor"), show: true },
    { href: "/admin/faqs", label: "FAQ", show: isAdmin },
    { href: "/admin/chatbot", label: t(locale, "panel.chatbot"), show: isAdmin },
    { href: "/admin/asesores", label: t(locale, "panel.team"), show: isAdmin },
    { href: "/admin/auditoria", label: t(locale, "home.audit"), show: isAdmin },
    { href: "/plataforma", label: t(locale, "platform.title"), show: user.is_platform_admin === true },
    { href: "/plataforma/auditoria", label: t(locale, "platform.audit"), show: user.is_platform_admin === true },
  ];
  return (
    <div className="panel-nav">
      <nav className="tabs" aria-label={t(locale, "panel.title")}>
        {links
          .filter((link) => link.show)
          .map((link) => (
            <Link key={link.href} href={link.href} aria-current={link.href === current ? "page" : undefined}>
              {link.label}
            </Link>
          ))}
      </nav>
      {(memberships.length > 1 || user.is_platform_admin) && memberships.length > 0 && (
        <form action={selectBusinessAction} className="business-switcher">
          <input type="hidden" name="next" value={current} />
          <label>
            {t(locale, "panel.business")}{" "}
            <select name="business" defaultValue={String(user.business?.id ?? "")} data-testid="business-select">
              {memberships.map((m) => (
                <option key={m.business_id} value={m.business_id}>
                  {m.business_name}
                  {m.is_active ? "" : ` (${t(locale, "platform.suspended")})`}
                </option>
              ))}
            </select>
          </label>{" "}
          <button type="submit" className="secondary">
            {t(locale, "panel.switch")}
          </button>
        </form>
      )}
      {user.business && (
        <p className="muted" data-testid="current-business">
          {t(locale, "panel.currentBusiness")}: <strong>{user.business.name}</strong>
        </p>
      )}
    </div>
  );
}
