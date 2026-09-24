const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
let token: string | null = null;

async function getToken() {
  if (token) return token;
  const r = await fetch(`${BASE}/v1/auth/dev-token`, { method: "POST" }); // dev only
  token = (await r.json()).access_token as string;
  return token;
}
export class ApiFail extends Error { constructor(public code: string, msg: string, public retryAfter?: number) { super(msg); } }

export async function requestBuild(payload: object, signal: AbortSignal, idemKey: string) {
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
  return data;
}
