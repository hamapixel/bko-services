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
        url: "/icon.svg",
        type: "image/svg+xml",
        sizes: "any",
      },
      {
        url: "/icons/icon-192.png",
        type: "image/png",
        sizes: "192x192",
      },
      {
        url: "/icons/icon-512.png",
        type: "image/png",
        sizes: "512x512",
      },
    ],
    apple: "/icons/icon-192.png",
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
  viewportFit: "cover",
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
