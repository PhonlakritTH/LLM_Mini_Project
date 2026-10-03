const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
let token: string | null = null;

export type BuildResponse = {
  status: "complete" | "needs_info" | "degraded" | "budget_exhausted";
  questions: string[];
  recommendation_code: string;
  compatibility_status: "compatible" | "warning" | "incompatible";
  confidence: number | null;
  summary: string;
  reasons: string[];
  conflicts: string[];
  suggested_fix: string | null;
  parts_list: { type: string; name: string; price: number | null; in_stock: boolean | null; source: string | null; product_url: string | null; owned: boolean }[];
  price_breakdown: Record<string, number | null>;
  benchmark_estimate: { relative_score?: number; est_fps_1080p?: number } | null;
  sources: string[];
  partial_result: boolean;
  degraded_services: string[];
  data_quality: { total_price?: number | null };
  updated_at: string;
  conversation_id: string;
};

async function getToken() {
  if (token) return token;
  const r = await fetch(`${BASE}/v1/auth/dev-token`, { method: "POST" }); // dev only
  token = (await r.json()).access_token as string;
  return token;
}
export class ApiFail extends Error { constructor(public code: string, msg: string, public retryAfter?: number) { super(msg); } }

export async function requestBuild(payload: object, signal: AbortSignal, idemKey: string): Promise<BuildResponse> {
  const res = await fetch(`${BASE}/v1/builder/recommendations`, {
    method: "POST", signal,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${await getToken()}`, "Idempotency-Key": idemKey },
    body: JSON.stringify(payload),
  });
  if (res.status === 401) token = null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiFail(data?.error?.code ?? "HTTP_" + res.status,
    res.status === 429 ? "Too many requests. Please wait a moment." : data?.error?.message ?? "Request failed.",
    Number(res.headers.get("Retry-After") ?? 0) || undefined);
  return data as BuildResponse;
}
