import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Chatbot Black Dog Store", template: "%s | Chatbot Black Dog Store" },
  description: "Prototipo académico de atención automatizada",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
