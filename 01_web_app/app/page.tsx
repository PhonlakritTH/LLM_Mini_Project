"use client";
import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowRight, ArrowUpRight, Check, Cpu, Gauge, Moon, Sparkles, Sun } from "lucide-react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { formSchema, FormValues, normalize, USE_CASES, PART_TYPES } from "@/lib/schema";
import { requestBuild, ApiFail, BuildResponse } from "@/lib/api";

const ACTIONS: Record<string, string> = {
  finalize_build: "ชุดสเปกอยู่ในงบ", swap_component: "ปรับชุดสเปก",
  reconfigure_build: "ชุดสเปกเกินงบ", needs_price_data: "ยังประเมินงบไม่ได้", avoid_combination: "ไม่ควรใช้ชุดนี้ร่วมกัน",
};
const STATUS: Record<string, [string, string]> = { compatible: ["✓", "เข้ากันได้"], warning: ["!", "ควรตรวจสอบ"], incompatible: ["×", "ไม่เข้ากัน"] };
const baht = (n: number) => new Intl.NumberFormat("th-TH", { style: "currency", currency: "THB", maximumFractionDigits: 0 }).format(n);

type Theme = "light" | "dark";

function Hero({ theme, onToggleTheme }: { theme: Theme; onToggleTheme: () => void }) {
  return (
    <section className="hero" id="home">
      <header className="site-header">
        <a className="brand" href="#home" aria-label="SPECROOM หน้าแรก">
          <span className="brand-mark"><Cpu size={19} strokeWidth={2.2} /></span>
          <span>SPECROOM<span className="brand-period">.</span><small>PC CONFIGURATOR</small></span>
        </a>
        <nav className="site-nav" aria-label="เมนูหลัก">
          <a className="active" href="#home">หน้าแรก</a>
          <a href="#builder">จัดสเปก</a>
          <a href="#about">เกี่ยวกับเรา</a>
        </nav>
        <div className="header-actions">
          <a className="header-cta" href="#builder">เริ่มต้นเลย <ArrowUpRight size={15} /></a>
          <button
            className="theme-toggle"
            type="button"
            onClick={onToggleTheme}
            aria-label={theme === "dark" ? "เปลี่ยนเป็น Light mode" : "เปลี่ยนเป็น Dark mode"}
            title={theme === "dark" ? "Light mode" : "Dark mode"}
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </header>

      <div className="hero-content">
        <div className="hero-copy">
          <div className="eyebrow"><span /> BUILT AROUND YOU</div>
          <h1>คอมพิวเตอร์ที่ใช่<br /><span>เริ่มจากสเปกที่ลงตัว</span></h1>
          <p className="hero-description">
            ทุกการใช้งานมีสเปกที่เหมาะ ไม่ว่าจะเล่นเกม ทำงานสร้างสรรค์
            หรือเริ่มต้นกับ AI — วางแผนเครื่องถัดไปของคุณได้ที่นี่
          </p>
          <div className="hero-actions">
            <a className="button-primary" href="#builder">เริ่มจัดสเปก <ArrowDown size={17} /></a>
            <a className="button-secondary" href="#builder">ดูวิธีการทำงาน <ArrowRight size={16} /></a>
          </div>
          <div className="hero-benefits">
            <div><span className="benefit-number">01</span><span>สเปกตามงบ<br /><small>เลือกได้ตามต้องการ</small></span></div>
            <div><span className="benefit-number">02</span><span>เช็กความเข้ากันได้<br /><small>ลดปัญหาก่อนประกอบ</small></span></div>
            <div><span className="benefit-number">03</span><span>มีผู้ช่วยแนะนำ<br /><small>ตัดสินใจได้ง่ายขึ้น</small></span></div>
          </div>
        </div>

        <div className="hero-art" aria-label="ภาพจำลองคอมพิวเตอร์สำหรับจัดสเปก" role="img">
          <div className="art-glow" />
          <div className="art-label"><span>YOUR NEXT BUILD</span><span>01 — 03</span></div>
          <div className="pc-tower">
            <div className="tower-glass">
              <div className="tower-topline" />
              <div className="fan fan-one"><i /></div>
              <div className="fan fan-two"><i /></div>
              <div className="fan fan-three"><i /></div>
              <div className="gpu"><span /><span /><span /></div>
              <div className="motherboard"><i /><i /><i /></div>
              <div className="tower-light" />
            </div>
            <div className="tower-front"><span /><span /><span /><span /></div>
            <div className="tower-foot" />
          </div>
          <div className="art-spec spec-processor"><Cpu size={16} /><span>PROCESSOR<small>Performance, perfected.</small></span><Check size={15} /></div>
          <div className="art-spec spec-balance"><Gauge size={17} /><span>BUILD BALANCE<small>ทุกชิ้นส่วนลงตัว</small></span></div>
          <div className="art-caption"><Sparkles size={13} /> DESIGNED FOR WHAT YOU DO</div>
        </div>
      </div>

      <a className="scroll-cue" href="#builder"><span>เลื่อนเพื่อเริ่มต้น</span><ArrowDown size={15} /></a>
    </section>
  );
}

export default function Page() {
  const [theme, setTheme] = useState<Theme>("light");
  useEffect(() => {
    const savedTheme = window.localStorage.getItem("specroom-theme");
    const initialTheme: Theme = savedTheme === "light" || savedTheme === "dark"
      ? savedTheme
      : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    setTheme(initialTheme);
    document.documentElement.dataset.theme = initialTheme;
  }, []);

  function toggleTheme() {
    const nextTheme: Theme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;
    window.localStorage.setItem("specroom-theme", nextTheme);
  }

  const { register, control, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { budget: 40000, use_case: "gaming", preferred_brand: "any", preferred_gpu_brand: "any", preferred_cpu_model: "", preferred_gpu_model: "", existing_parts: [], question: "" },
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
    <>
      <Hero theme={theme} onToggleTheme={toggleTheme} />
      <main className="builder-layout" id="builder">
      <div className="builder-heading">
        <div className="eyebrow"><span /> PC BUILDER</div>
        <h2>เริ่มจากความต้องการของคุณ</h2>
        <p>กำหนดงบ การใช้งาน และรุ่นที่สนใจ เพื่อรับชุดสเปกพร้อมราคาอ้างอิง</p>
      </div>
      <form className="card" onSubmit={handleSubmit((v) => setPending(normalize(v)))} noValidate>
        <h2>ความต้องการ</h2>
        <label htmlFor="budget">งบประมาณ (บาท)</label>
        <input id="budget" type="number" inputMode="numeric" {...register("budget")} aria-invalid={!!errors.budget} />
        {errors.budget && <p className="err" role="alert">⚠ {errors.budget.message}</p>}
        <label htmlFor="uc">ลักษณะการใช้งาน</label>
        <select id="uc" {...register("use_case")}>{Object.entries(USE_CASES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <label htmlFor="br">แบรนด์ CPU</label>
        <select id="br" {...register("preferred_brand")}>
          <option value="any">ไม่ระบุ</option><option value="intel">Intel</option><option value="amd">AMD</option>
        </select>
        <label htmlFor="gpu-brand">แบรนด์ GPU (ไม่บังคับ)</label>
        <select id="gpu-brand" {...register("preferred_gpu_brand")}>
          <option value="any">ไม่ระบุ</option><option value="nvidia">NVIDIA</option><option value="amd">AMD Radeon</option>
        </select>
        <label htmlFor="cpu-model">รุ่น CPU ที่สนใจ (ไม่บังคับ)</label>
        <input id="cpu-model" placeholder="เช่น Ryzen 5 7600" {...register("preferred_cpu_model")} />
        <label htmlFor="gpu-model">รุ่น GPU ที่สนใจ (ไม่บังคับ)</label>
        <input id="gpu-model" placeholder="เช่น RTX 4060" {...register("preferred_gpu_model")} />
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
            <p>{baht(pending.budget)} · {USE_CASES[pending.use_case]} · CPU: {pending.preferred_brand} · GPU: {pending.preferred_gpu_brand}{pending.preferred_cpu_model && ` · รุ่น CPU: ${pending.preferred_cpu_model}`}{pending.preferred_gpu_model && ` · รุ่น GPU: ${pending.preferred_gpu_model}`} · ชิ้นส่วนเดิม: {pending.existing_parts.map((p) => p.name).join(", ") || "ไม่มี"}</p>
            <button onClick={send} disabled={state === "loading"}>{state === "loading" ? "กำลังตรวจสอบ…" : "จัดสเปก"}</button>{" "}
            <button className="ghost" onClick={() => setPending(null)}>แก้ไข</button>
          </div>
        )}
        {state === "idle" && !pending && <div className="card"><h2>ยังไม่มีผลจัดสเปก</h2><p>กรอกความต้องการแล้วตรวจสอบคำขอเพื่อเริ่มต้น</p></div>}
        {state === "loading" && <div className="card" role="status">{progress}</div>}
        {state === "error" && <div className="banner incompatible" role="alert">{msg}</div>}
        {state === "done" && res && <Result r={res} />}
      </section>
      <footer className="builder-footer" id="about">SPECROOM <span>·</span> วางแผนสเปกคอมในแบบของคุณ</footer>
      </main>
    </>
  );
}

// All server/LLM text is rendered as plain React text nodes (auto-escaped) — no dangerouslySetInnerHTML.
function Result({ r }: { r: BuildResponse }) {
  const [icon, label] = STATUS[r.compatibility_status] ?? STATUS.warning;
  const knownTotal = r.data_quality.total_price;
  const totalRange = r.data_quality.total_price_range;
  const shownTotal = typeof knownTotal === "number" ? knownTotal : totalRange ? (totalRange.low + totalRange.high) / 2 : null;
  return (
    <div className="card">
      <h2>{ACTIONS[r.recommendation_code] ?? "ผลการจัดสเปก"}</h2>
      <div className={`banner ${r.compatibility_status}`}>{icon} {label}<br />{r.summary}</div>
      {r.questions.length > 0 && <ul>{r.questions.map((question) => <li key={question}>{question}</li>)}</ul>}
      {r.partial_result && <div className="banner warning">ข้อมูลยังไม่ครบ: {r.degraded_services.join(", ") || "บางบริการ"} ไม่พร้อมใช้งาน</div>}
      {r.conflicts.length > 0 && <div className="banner incompatible"><strong>ข้อขัดแย้ง</strong><ul>{r.conflicts.map((conflict) => <li key={conflict}>{conflict}</li>)}</ul>{r.suggested_fix && <p>วิธีแก้: {r.suggested_fix}</p>}</div>}
      <ul>{r.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
      {r.limitations.length > 0 && <div className="banner warning"><strong>ข้อจำกัดของข้อมูล</strong><ul>{r.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></div>}
      <table>
        <thead><tr><th>ชิ้นส่วน</th><th>รุ่นและที่มาสเปก</th><th className="n">ราคาอ้างอิง</th></tr></thead>
        <tbody>{r.parts_list.map((part) => (
          <tr key={part.type}><td>{part.type}</td><td>{part.name}
            {part.spec_source && <small className="source"><a href={part.spec_source} target="_blank" rel="noreferrer">แหล่งสเปกจากผู้ผลิต</a></small>}
            {part.price_source && <small className="source">{part.price_source}</small>}</td>
            <td className="n">{part.owned ? "ใช้ชิ้นส่วนเดิม" : part.price_low !== null && part.price_high !== null
              ? `${baht(part.price_low)} – ${baht(part.price_high)}` : "ไม่มีราคาอ้างอิง"}</td></tr>))}
          <tr><th colSpan={2}>ราคารวมอ้างอิง (ไม่ใช่ใบเสนอราคา)</th><th className="n">{totalRange
            ? `${baht(totalRange.low)} – ${baht(totalRange.high)}`
            : shownTotal !== null ? baht(shownTotal) : "ประเมินไม่ได้: ราคาไม่ครบ"}</th></tr></tbody>
      </table>
      {r.data_quality.price_reference_note && <p>{r.data_quality.price_reference_note}</p>}
      {r.data_quality.price_reference_observed_at && <p>ค้นหาราคาอ้างอิงเมื่อ {new Date(r.data_quality.price_reference_observed_at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}</p>}
      <details><summary>แหล่งข้อมูล</summary>{r.sources.length ? <ul>{r.sources.map((source) => <li key={source}>{source}</li>)}</ul> : "ไม่มีแหล่งข้อมูลที่ยืนยันได้"}</details>
      <p style={{ color: "var(--mute)", fontSize: ".85rem" }}>ปรับปรุงข้อมูล {new Date(r.updated_at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}</p>
    </div>
  );
}
