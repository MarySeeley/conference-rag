import { createClient } from "jsr:@supabase/supabase-js@2";
import { corsHeaders } from "./cors.ts";

type AuthenticatedUser = {
  id: string;
  email?: string;
};

type AuthResult =
  | { user: AuthenticatedUser }
  | { error: Response };

/**
 * Verify the caller's bearer token with Supabase Auth.
 *
 * The assignment deploys with gateway JWT verification disabled, so this check
 * must run before any paid OpenAI request is made.
 */
export async function requireAuth(req: Request): Promise<AuthResult> {
  const headers = corsHeaders(req);
  const authHeader = req.headers.get("Authorization");

  if (!authHeader?.startsWith("Bearer ")) {
    return {
      error: Response.json(
        { error: "Missing or invalid Authorization header" },
        { status: 401, headers },
      ),
    };
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY");

  if (!supabaseUrl || !supabaseAnonKey) {
    console.error("Supabase function environment is not configured");
    return {
      error: Response.json(
        { error: "Authentication service is not configured" },
        { status: 500, headers },
      ),
    };
  }

  const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    global: { headers: { Authorization: authHeader } },
  });

  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error || !user) {
    return {
      error: Response.json(
        { error: "Invalid or expired token" },
        { status: 401, headers },
      ),
    };
  }

  return {
    user: {
      id: user.id,
      email: user.email,
    },
  };
}
