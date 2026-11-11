
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Desactivar temporalmente Cache Components.
  // Permite utilizar cookies para el selector de idioma.
  cacheComponents: false,

  // Mantener la configuración para Docker y Render.
  output: "standalone",

  // El navegador recibe el código minificado, sin mapas que reconstruyan el fuente
  // (es el valor por defecto; se deja explícito y la CI lo comprueba).
  productionBrowserSourceMaps: false,
};

export default nextConfig;
