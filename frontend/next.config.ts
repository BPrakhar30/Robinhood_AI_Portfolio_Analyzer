import type { NextConfig } from "next";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-XSS-Protection", value: "1; mode=block" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // microphone=(self)  -  required for the assistant's voice-to-text input
  { key: "Permissions-Policy", value: "camera=(), microphone=(self), geolocation=()" },
];

if (process.env.NODE_ENV === "production") {
  securityHeaders.push(
    {
      key: "Strict-Transport-Security",
      value: "max-age=63072000; includeSubDomains; preload",
    },
    {
      key: "Content-Security-Policy",
      value: [
        "default-src 'self'",
        // Keep 'unsafe-inline' for Next.js inline bootstrap scripts; avoid unsafe-eval.
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "connect-src 'self' https:",
        "font-src 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
      ].join("; "),
    }
  );
}

const nextConfig: NextConfig = {
  allowedDevOrigins: ["10.0.0.131", "localhost", "127.0.0.1"],
  poweredByHeader: false,
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;
