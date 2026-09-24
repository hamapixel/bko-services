import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import PwaClient from "@/components/pwa-client";

import "./globals.css";

export const metadata: Metadata = {
  title: "BKO Services",
  description: "Le bon professionnel, au bon moment à Bamako.",
  applicationName: "BKO Services",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      {
        url: "/icons/icon-192.svg",
        type: "image/svg+xml",
        sizes: "192x192",
      },
      {
        url: "/icons/icon-512.svg",
        type: "image/svg+xml",
        sizes: "512x512",
      },
    ],
    apple: "/icons/icon-192.svg",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "BKO Services",
  },
  formatDetection: {
    telephone: false,
  },
};

export const viewport: Viewport = {
  themeColor: "#102e55",
  colorScheme: "light",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        {children}
        <PwaClient />
      </body>
    </html>
  );
}
