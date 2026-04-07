import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { Providers } from "@/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "RobinhoodAI Copilot",
  description: "AI Portfolio Copilot for Robinhood users — securely connect, analyze, and optimize your portfolio.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`} suppressHydrationWarning>
        {/* Runs before React hydration to suppress attribute-mismatch warnings
            caused by browser extensions injecting DOM attributes (e.g. rtrvr-*). */}
        <Script
          id="suppress-hydration-warning"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(){var oe=console.error,ow=console.warn;function f(a){return typeof a==='string'&&a.indexOf('hydrat')!==-1}console.error=function(){if(f(arguments[0]))return;oe.apply(console,arguments)};console.warn=function(){if(f(arguments[0]))return;ow.apply(console,arguments)};})();`,
          }}
        />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
