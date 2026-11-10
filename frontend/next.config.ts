
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Desactivar temporalmente Cache Components.
  // Permite utilizar cookies para el selector de idioma.
  cacheComponents: false,

  // Mantener la configuración para Docker y Render.
  output: "standalone",
};

export default nextConfig;
