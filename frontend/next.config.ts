import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // Servidor autocontenido para la imagen Docker.
  output: "standalone",
};

export default nextConfig;
