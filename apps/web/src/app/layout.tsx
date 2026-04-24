import type { Metadata } from "next";
import { Geist, Geist_Mono, IBM_Plex_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { ConditionalNav } from "@/components/conditional-nav";
import { CommandPalette } from "@/components/command-palette";
import { SettingsDialog } from "@/components/settings-dialog";
import { GlobalShortcuts } from "@/components/global-shortcuts";
import { ErrorBoundary } from "@/components/error-boundary";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
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
      className={`${geistSans.variable} ${geistMono.variable} ${ibmPlexMono.variable} ${spaceGrotesk.variable} dark antialiased`}
    >
      <body className="h-dvh flex flex-col bg-background text-foreground overflow-hidden">
        <ErrorBoundary>
          <Providers>
            <GlobalShortcuts />
            <ConditionalNav />
            <main className="flex-1 min-h-0 flex flex-col">{children}</main>
            <CommandPalette />
            <SettingsDialog />
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}