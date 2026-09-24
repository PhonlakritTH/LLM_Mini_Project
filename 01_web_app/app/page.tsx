"use client";
import { useRef, useState } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { formSchema, FormValues, normalize, USE_CASES, PART_TYPES } from "@/lib/schema";
import { requestBuild, ApiFail } from "@/lib/api";

const ACTIONS: Record<string, string> = {
  finalize_build: "Finalize build", swap_component: "Swap a component",
  wait_for_price_drop: "Wait for a price drop", avoid_combination: "Avoid this combination",
};
const STATUS: Record<string, [string, string]> = { compatible: ["✅", "Compatible"], warning: ["⚠️", "Warning"], incompatible: ["❌", "Incompatible"] };
const baht = (n: number) => new Intl.NumberFormat("th-TH", { style: "currency", currency: "THB", maximumFractionDigits: 0 }).format(n);

export default function Page() {
  const { register, control, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { budget: 40000, use_case: "gaming", preferred_brand: "any", existing_parts: [], question: "" },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "existing_parts" });
  const [pending, setPending] = useState<ReturnType<typeof normalize> | null>(null); // confirm panel (step 4)
  const [state, setState] = useState<"idle" | "loading" | "error" | "done">("idle");
  const [progress, setProgress] = useState("");
  const [msg, setMsg] = useState("");
  const [res, setRes] = useState<any>(null);
  const ctrl = useRef<AbortController | null>(null);
  const convId = useRef<string | undefined>(undefined);

  async function send() {
    if (!pending || state === "loading") return;          // block duplicate submit
    ctrl.current?.abort();                                  // cancel stale request
    ctrl.current = new AbortController();
    const rid = crypto.randomUUID();
    setState("loading"); setRes(null);
    const steps = ["Checking prices…", "Checking stock…", "Checking compatibility…"];
    let i = 0; setProgress(steps[0]);
    const t = setInterval(() => setProgress(steps[++i % steps.length]), 900);
    try {
      const data = await requestBuild({ ...pending, request_id: rid, conversation_id: convId.current, locale: "th-TH" }, ctrl.current.signal, rid);
      convId.current = data.conversation_id; setRes(data); setState("done"); setPending(null);
    } catch (e: any) {
      if (e.name === "AbortError") return;
      setMsg(e instanceof ApiFail ? e.message : "Cannot reach the server. Check your connection and try again."); setState("error");
    } finally { clearInterval(t); }
  }

  return (
    <main>
      <h1>PC Spec Builder<small>Get a compatibility-checked build for your budget.</small></h1>
      <form className="card" onSubmit={handleSubmit((v) => setPending(normalize(v)))} noValidate>
        <h2>Your requirements</h2>
        <label htmlFor="budget">Budget (THB)</label>
        <input id="budget" type="number" inputMode="numeric" {...register("budget")} aria-invalid={!!errors.budget} />
        {errors.budget && <p className="err" role="alert">⚠ {errors.budget.message}</p>}
        <label htmlFor="uc">Use case</label>
        <select id="uc" {...register("use_case")}>{Object.entries(USE_CASES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <label htmlFor="br">Preferred brand</label>
        <select id="br" {...register("preferred_brand")}>
          <option value="any">No preference</option><option value="intel">Intel CPU</option><option value="amd">AMD CPU / GPU</option><option value="nvidia">NVIDIA GPU</option>
        </select>
        <label>Parts you already own</label>
        {fields.map((f, i) => (
          <div className="row" key={f.id}>
            <select aria-label="Part type" {...register(`existing_parts.${i}.type`)}>{PART_TYPES.map((t) => <option key={t}>{t}</option>)}</select>
            <input aria-label="Part name" placeholder="Name" {...register(`existing_parts.${i}.name`)} />
            <input aria-label="Socket" placeholder="Socket" {...register(`existing_parts.${i}.socket`)} />
            <button type="button" className="ghost" style={{ margin: 0, padding: 4 }} aria-label="Remove part" onClick={() => remove(i)}>✕</button>
          </div>
        ))}
        {errors.existing_parts && <p className="err" role="alert">⚠ Every owned part needs a name.</p>}
        <button type="button" className="ghost" onClick={() => append({ type: "motherboard", name: "", socket: "" })} disabled={fields.length >= 10}>+ Add part</button>
        <label htmlFor="q">Question (optional)</label>
        <textarea id="q" rows={3} maxLength={500} {...register("question")} />
        <button type="submit">Review request</button>
      </form>

      <section aria-live="polite">
        {pending && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h2>Confirm your request</h2>
            <p>{baht(pending.budget)} · {USE_CASES[pending.use_case]} · brand: {pending.preferred_brand} · owned parts: {pending.existing_parts.map((p) => p.name).join(", ") || "none"}</p>
            <button onClick={send} disabled={state === "loading"}>{state === "loading" ? "Working…" : "Get recommendation"}</button>{" "}
            <button className="ghost" onClick={() => setPending(null)}>Edit</button>
          </div>
        )}
        {state === "idle" && !pending && <div className="card"><h2>No build yet</h2><p>Fill in the form and review your request to see a recommended build.</p></div>}
        {state === "loading" && <div className="card" role="status">⏳ {progress}</div>}
        {state === "error" && <div className="banner incompatible" role="alert">❌ {msg}</div>}
        {state === "done" && res && <Result r={res} />}
      </section>
    </main>
  );
}

// All server/LLM text is rendered as plain React text nodes (auto-escaped) — no dangerouslySetInnerHTML.
function Result({ r }: { r: any }) {
  const [icon, label] = STATUS[r.compatibility_status];
  const prices = Object.values(r.price_breakdown) as number[];
  const max = Math.max(...prices, 1), total = prices.reduce((a, b) => a + b, 0);
  return (
    <div className="card">
      <h2>Recommended action: {ACTIONS[r.recommendation_code]}</h2>
      <div className={`banner ${r.compatibility_status}`}>{icon} {label} · confidence {Math.round(r.confidence * 100)}%<br />{r.summary}</div>
      {r.partial_result && <div className="banner warning">⚠️ Partial result: {r.degraded_services.join(", ")} unavailable, so stock is unverified.</div>}
      {r.conflicts.length > 0 && <div className="banner incompatible"><strong>❌ Conflicts</strong><ul>{r.conflicts.map((c: string) => <li key={c}>{c}</li>)}</ul>{r.suggested_fix && <p>Suggested fix: {r.suggested_fix}</p>}</div>}
      <ul>{r.reasons.map((x: string) => <li key={x}>{x}</li>)}</ul>
      <table>
        <thead><tr><th>Part</th><th>Model</th><th>Stock</th><th className="n">Price</th></tr></thead>
        <tbody>{r.parts_list.map((p: any) => (
          <tr key={p.type}><td>{p.type}</td><td>{p.name}</td><td>{p.in_stock === null ? "Unknown" : p.in_stock ? "In stock" : "Out of stock"}</td>
            <td className="n">{baht(p.price)}<div className="bar" style={{ width: `${(p.price / max) * 100}%` }} /></td></tr>))}
          <tr><th colSpan={3}>Total</th><th className="n">{baht(total)}</th></tr></tbody>
      </table>
      <details><summary>Benchmark estimate</summary>Relative score {r.benchmark_estimate.relative_score}/100 · about {r.benchmark_estimate.est_fps_1080p} FPS at 1080p</details>
      <details><summary>Sources</summary><ul>{r.sources.map((s: string) => <li key={s}>{s}</li>)}</ul></details>
      <p style={{ color: "var(--mute)", fontSize: ".85rem" }}>Updated {new Date(r.updated_at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}. To ask a follow-up, edit the form and send again; it keeps the same conversation.</p>
    </div>
  );
}
