const allowedOrigins = new Set([
  "https://maryseeley.github.io",
  "http://localhost:5500",
  "http://127.0.0.1:5500",
]);

/**
 * Return CORS headers for this app's deployed site and local development server.
 * An unrecognized Origin receives the production origin, so a browser will reject
 * the response because it does not match the requesting site.
 */
export function corsHeaders(req: Request): Record<string, string> {
  const requestOrigin = req.headers.get("Origin");
  const allowedOrigin = requestOrigin && allowedOrigins.has(requestOrigin)
    ? requestOrigin
    : "https://maryseeley.github.io";

  return {
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Headers":
      "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Vary": "Origin",
  };
}
