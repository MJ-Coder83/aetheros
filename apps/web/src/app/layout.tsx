import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Navbar } from "@/components/navbar";
import { CommandPalette } from "@/components/command-palette";
import { SettingsDialog } from "@/components/settings-dialog";
import { GlobalShortcuts } from "@/components/global-shortcuts";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "InkosAI — Self-Governing AI Operating System",
  description:
    "Interact with Prime, view the Tape, manage proposals, and run simulations.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>
          <GlobalShortcuts />
          <Navbar />
          <main className="flex-1">{children}</main>
          <CommandPalette />
          <SettingsDialog />
        </Providers>
      </body>
    </html>
  );
}
