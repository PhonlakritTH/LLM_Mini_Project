"use client";
import { useRef, useState } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { formSchema, FormValues, normalize, USE_CASES, PART_TYPES } from "@/lib/schema";
import { requestBuild, ApiFail, BuildResponse } from "@/lib/api";

const ACTIONS: Record<string, string> = {
  finalize_build: "จัดสเปกนี้ได้", swap_component: "ควรเปลี่ยนชิ้นส่วน",
  wait_for_price_drop: "รอข้อมูลหรือราคา", avoid_combination: "ไม่ควรใช้ชุดนี้ร่วมกัน",
};
const STATUS: Record<string, [string, string]> = { compatible: ["✓", "เข้ากันได้"], warning: ["!", "ควรตรวจสอบ"], incompatible: ["×", "ไม่เข้ากัน"] };
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
  const [res, setRes] = useState<BuildResponse | null>(null);
  const ctrl = useRef<AbortController | null>(null);
  const convId = useRef<string | undefined>(undefined);

  async function send() {
    if (!pending || state === "loading") return;          // block duplicate submit
    ctrl.current?.abort();                                  // cancel stale request
    ctrl.current = new AbortController();
    const rid = crypto.randomUUID();
    setState("loading"); setRes(null);
    setProgress("กำลังตรวจสอบข้อมูลและความเข้ากันได้…");
    try {
      const data = await requestBuild({ ...pending, request_id: rid, conversation_id: convId.current, locale: "th-TH" }, ctrl.current.signal, rid);
      convId.current = data.conversation_id; setRes(data); setState("done"); setPending(null);
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setMsg(e instanceof ApiFail ? e.message : "เชื่อมต่อระบบไม่ได้ กรุณาตรวจสอบการเชื่อมต่อแล้วลองอีกครั้ง"); setState("error");
    }
  }

  return (
    <main>
      <h1>จัดสเปกคอม<small>ค้นหาราคาและตรวจสอบความเข้ากันได้ตามงบประมาณ</small></h1>
      <form className="card" onSubmit={handleSubmit((v) => setPending(normalize(v)))} noValidate>
        <h2>ความต้องการ</h2>
        <label htmlFor="budget">งบประมาณ (บาท)</label>
        <input id="budget" type="number" inputMode="numeric" {...register("budget")} aria-invalid={!!errors.budget} />
        {errors.budget && <p className="err" role="alert">⚠ {errors.budget.message}</p>}
        <label htmlFor="uc">ลักษณะการใช้งาน</label>
        <select id="uc" {...register("use_case")}>{Object.entries(USE_CASES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <label htmlFor="br">แบรนด์ที่ต้องการ</label>
        <select id="br" {...register("preferred_brand")}>
          <option value="any">ไม่ระบุ</option><option value="intel">Intel CPU</option><option value="amd">AMD CPU / GPU</option><option value="nvidia">NVIDIA GPU</option>
        </select>
        <label>ชิ้นส่วนที่มีอยู่แล้ว</label>
        {fields.map((f, i) => (
          <div className="row" key={f.id}>
            <select aria-label="Part type" {...register(`existing_parts.${i}.type`)}>{PART_TYPES.map((t) => <option key={t}>{t}</option>)}</select>
            <input aria-label="ชื่อชิ้นส่วน" placeholder="ชื่อรุ่น" {...register(`existing_parts.${i}.name`)} />
            <input aria-label="ซ็อกเก็ต" placeholder="Socket" {...register(`existing_parts.${i}.socket`)} />
            <input aria-label="กำลังไฟ PSU" placeholder="Wattage (PSU)" type="number" inputMode="numeric" {...register(`existing_parts.${i}.wattage`)} />
            <button type="button" className="ghost" style={{ margin: 0, padding: 4 }} aria-label="ลบชิ้นส่วน" onClick={() => remove(i)}>×</button>
          </div>
        ))}
        {errors.existing_parts && <p className="err" role="alert">กรุณาระบุชื่อรุ่นของชิ้นส่วนที่มีอยู่</p>}
        <button type="button" className="ghost" onClick={() => append({ type: "motherboard", name: "", socket: "" })} disabled={fields.length >= 10}>+ เพิ่มชิ้นส่วน</button>
        <label htmlFor="q">คำถามเพิ่มเติม (ไม่บังคับ)</label>
        <textarea id="q" rows={3} maxLength={500} {...register("question")} />
        <button type="submit">ตรวจสอบคำขอ</button>
      </form>

      <section aria-live="polite">
        {pending && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h2>ยืนยันคำขอ</h2>
            <p>{baht(pending.budget)} · {USE_CASES[pending.use_case]} · {pending.preferred_brand} · ชิ้นส่วนเดิม: {pending.existing_parts.map((p) => p.name).join(", ") || "ไม่มี"}</p>
            <button onClick={send} disabled={state === "loading"}>{state === "loading" ? "กำลังตรวจสอบ…" : "จัดสเปก"}</button>{" "}
            <button className="ghost" onClick={() => setPending(null)}>แก้ไข</button>
          </div>
        )}
        {state === "idle" && !pending && <div className="card"><h2>ยังไม่มีผลจัดสเปก</h2><p>กรอกความต้องการแล้วตรวจสอบคำขอเพื่อเริ่มต้น</p></div>}
        {state === "loading" && <div className="card" role="status">{progress}</div>}
        {state === "error" && <div className="banner incompatible" role="alert">{msg}</div>}
        {state === "done" && res && <Result r={res} />}
      </section>
    </main>
  );
}

// All server/LLM text is rendered as plain React text nodes (auto-escaped) — no dangerouslySetInnerHTML.
function Result({ r }: { r: BuildResponse }) {
  const [icon, label] = STATUS[r.compatibility_status] ?? STATUS.warning;
  const prices = r.parts_list.map((part) => part.price).filter((price): price is number => price !== null);
  const max = Math.max(...prices, 1);
  const knownTotal = r.data_quality.total_price;
  const shownTotal = typeof knownTotal === "number" ? knownTotal : prices.reduce((sum, price) => sum + price, 0);
  return (
    <div className="card">
      <h2>{ACTIONS[r.recommendation_code] ?? "ผลการจัดสเปก"}</h2>
      <div className={`banner ${r.compatibility_status}`}>{icon} {label}<br />{r.summary}</div>
      {r.questions.length > 0 && <ul>{r.questions.map((question) => <li key={question}>{question}</li>)}</ul>}
      {r.partial_result && <div className="banner warning">ข้อมูลยังไม่ครบ: {r.degraded_services.join(", ") || "บางบริการ"} ไม่พร้อมใช้งาน</div>}
      {r.conflicts.length > 0 && <div className="banner incompatible"><strong>ข้อขัดแย้ง</strong><ul>{r.conflicts.map((conflict) => <li key={conflict}>{conflict}</li>)}</ul>{r.suggested_fix && <p>วิธีแก้: {r.suggested_fix}</p>}</div>}
      <ul>{r.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
      <table>
        <thead><tr><th>ชิ้นส่วน</th><th>รุ่น</th><th>สต็อก</th><th className="n">ราคา</th></tr></thead>
        <tbody>{r.parts_list.map((part) => (
          <tr key={part.type}><td>{part.type}</td><td>{part.product_url ? <a href={part.product_url} target="_blank" rel="noreferrer">{part.name}</a> : part.name}{part.source && <small className="source">{part.source}</small>}</td>
            <td>{part.in_stock === null ? "ยังไม่ทราบ" : part.in_stock ? "มีสินค้า" : "หมด"}</td>
            <td className="n">{part.owned ? "มีอยู่แล้ว" : part.price === null ? "ไม่พบราคา" : baht(part.price)}{!part.owned && part.price !== null && <div className="bar" style={{ width: `${(part.price / max) * 100}%` }} />}</td></tr>))}
          <tr><th colSpan={3}>{typeof knownTotal === "number" ? "รวม" : "ยอดเฉพาะรายการที่พบราคา (ยังไม่ครบ)"}</th><th className="n">{prices.length ? baht(shownTotal) : "ไม่พบราคา"}</th></tr></tbody>
      </table>
      <details><summary>ผล benchmark</summary>{r.benchmark_estimate ? `คะแนน ${r.benchmark_estimate.relative_score ?? "ไม่ทราบ"}/100 · ประมาณ ${r.benchmark_estimate.est_fps_1080p ?? "ไม่ทราบ"} FPS ที่ 1080p` : "ยังไม่มีแหล่ง benchmark ที่ยืนยันได้"}</details>
      <details><summary>แหล่งข้อมูล</summary>{r.sources.length ? <ul>{r.sources.map((source) => <li key={source}>{source}</li>)}</ul> : "ไม่มีแหล่งข้อมูลที่ยืนยันได้"}</details>
      <p style={{ color: "var(--mute)", fontSize: ".85rem" }}>ปรับปรุงข้อมูล {new Date(r.updated_at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}</p>
    </div>
  );
}
