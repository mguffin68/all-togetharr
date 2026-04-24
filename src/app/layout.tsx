import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "All Togetharr",
  description:
    "A privacy-focused management dashboard that unifies self-hosted media stack services.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-surface text-on-surface antialiased">
        <div
          className="min-h-screen"
          style={{ fontFamily: "var(--font-inter), Inter, sans-serif" }}
        >
          {children}
        </div>
      </body>
    </html>
  );
}
