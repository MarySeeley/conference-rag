import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { requireAuth } from "../_shared/auth.ts";
import { corsHeaders } from "../_shared/cors.ts";

const MAX_QUESTION_LENGTH = 4_000;

type EmbeddingResponse = {
  data?: Array<{ embedding?: number[] }>;
  error?: { message?: string };
};

Deno.serve(async (req) => {
  const headers = corsHeaders(req);

  // Browsers send this preflight request before the authenticated POST.
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers });
  }

  if (req.method !== "POST") {
    return Response.json(
      { error: "Method not allowed" },
      { status: 405, headers: { ...headers, Allow: "POST, OPTIONS" } },
    );
  }

  // Authenticate before parsing or making a paid request to OpenAI.
  const authResult = await requireAuth(req);
  if ("error" in authResult) return authResult.error;

  try {
    const body = await req.json().catch(() => null);
    const question = typeof body?.question === "string"
      ? body.question.trim()
      : "";

    if (!question) {
      return Response.json(
        { error: "Missing or invalid 'question' field" },
        { status: 400, headers },
      );
    }

    if (question.length > MAX_QUESTION_LENGTH) {
      return Response.json(
        { error: `Question must be ${MAX_QUESTION_LENGTH} characters or fewer` },
        { status: 400, headers },
      );
    }

    const openaiKey = Deno.env.get("OPENAI_API_KEY");
    if (!openaiKey) {
      console.error("OPENAI_API_KEY is not configured");
      return Response.json(
        { error: "Embedding service is not configured" },
        { status: 500, headers },
      );
    }

    const openaiResponse = await fetch("https://api.openai.com/v1/embeddings", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${openaiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "text-embedding-3-small",
        input: question,
        encoding_format: "float",
        dimensions: 1_536,
      }),
    });

    const openaiData = await openaiResponse.json() as EmbeddingResponse;

    if (!openaiResponse.ok) {
      console.error(
        "OpenAI embeddings request failed",
        openaiResponse.status,
        openaiData.error?.message ?? "Unknown error",
      );
      return Response.json(
        { error: "Embedding service request failed" },
        { status: openaiResponse.status, headers },
      );
    }

    const embedding = openaiData.data?.[0]?.embedding;
    if (!embedding || embedding.length !== 1_536) {
      console.error("OpenAI returned an invalid embedding response");
      return Response.json(
        { error: "Embedding service returned an invalid response" },
        { status: 502, headers },
      );
    }

    return Response.json({ embedding }, { headers });
  } catch (error) {
    console.error("embed-question failed", error);
    return Response.json(
      { error: "Unable to embed question" },
      { status: 500, headers },
    );
  }
});
