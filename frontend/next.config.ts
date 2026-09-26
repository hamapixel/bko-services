import type { NextConfig } from "next";

const apiOrigin = (process.env.BKO_API_ORIGIN ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);
const isDevelopment = process.env.NODE_ENV !== "production";

const nextConfig: NextConfig = {
  devIndicators: false,
  // Django/DRF routes use trailing slashes. Keep them intact before the API
  // rewrite and always proxy API paths to Django with a trailing slash.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*/",
        destination: `${apiOrigin}/api/:path*/`,
      },
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/api/:path*/`,
      },
    ];
  },
  async headers() {
    return [
      ...(isDevelopment
        ? [
            {
              source: "/_next/:path*",
              headers: [
                {
                  key: "Cache-Control",
                  value: "no-store, no-cache, must-revalidate",
                },
              ],
            },
          ]
        : []),
      {
        source: "/sw.js",
        headers: [
          {
            key: "Cache-Control",
            value: "no-cache, no-store, must-revalidate",
          },
          {
            key: "Service-Worker-Allowed",
            value: "/",
          },
        ],
      },
      {
        source: "/manifest.webmanifest",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=300, must-revalidate",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
