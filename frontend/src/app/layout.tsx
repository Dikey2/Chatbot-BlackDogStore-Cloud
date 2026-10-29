import type { Metadata } from "next";
import "./globals.css";
import { getLocale } from "@/lib/locale";
import { LocaleProvider } from "@/components/LocaleProvider";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";

export const metadata: Metadata = {
  title: { default: "Chatbot Black Dog Store", template: "%s | Chatbot Black Dog Store" },
  description: "Prototipo académico de atención automatizada",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const locale = await getLocale();
  return (
    <html lang={locale}>
      <body>
        <LocaleProvider locale={locale}>
          <LocaleSwitcher locale={locale} />
          {children}
        </LocaleProvider>
      </body>
    </html>
  );
}
