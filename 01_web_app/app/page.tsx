"use client";
import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowRight, ArrowUpRight, Check, Cpu, Gauge, Moon, Sparkles, Sun } from "lucide-react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { formSchema, FormValues, normalize, USE_CASES, PART_TYPES } from "@/lib/schema";
import { requestBuild, ApiFail, BuildResponse } from "@/lib/api";

const ACTIONS: Record<string, string> = {
  finalize_build: "ชุดสเปกอยู่ในงบ", swap_component: "ปรับชุดสเปก",
  reconfigure_build: "ชุดสเปกเกินงบ", needs_price_data: "ราคาอ้างอิงไม่ครบ",
  needs_review: "ต้องตรวจสอบก่อนยืนยัน", avoid_combination: "ไม่ควรใช้ชุดนี้ร่วมกัน",
};
const STATUS: Record<string, [string, string]> = { compatible: ["✓", "เข้ากันได้"], warning: ["!", "ควรตรวจสอบ"], incompatible: ["×", "ไม่เข้ากัน"] };
const DEGRADED_LABELS: Record<string, string> = {
  compatibility_evidence_unverified: "หลักฐานความเข้ากันได้จากผู้ผลิตยังยืนยันไม่ครบ",
  manufacturer_specs: "อ่านข้อมูลจากหน้าเว็บผู้ผลิตไม่ครบ",
};
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

function getBudgetInsight(budget: number): string {
  if (budget < 20000) return "💼 งบนี้เหมาะกับงานเอกสาร ท่องเว็บ เรียนออนไลน์ ทำงานทั่วไป และดูหนัง 4K ได้สบาย";
  if (budget < 30000) return "🎮 เล่นเกม 1080p ทั่วไป (เช่น Valorant, Genshin) และตัดต่อวิดีโอ/กราฟิกระดับเริ่มต้น";
  if (budget < 45000) return "⚡ เล่นเกม 1080p ปรับสุดลื่นๆ / 1440p (GTA V, Elden Ring), สตรีมเกม และตัดต่อวิดีโอ Full HD";
  if (budget < 65000) return "🔥 เล่นเกม 2K (1440p) คุณภาพสูง, ตัดต่อ 4K, งาน 3D, และเริ่มทดลองรันโมเดล AI";
  return "🚀 สเปกระดับท็อป รองรับ 4K Gaming, รัน Local AI / LLM, และงานคำนวณกราฟิกระดับ Professional";
}

const USE_CASE_CARDS = [
  { id: "gaming", icon: "🎮", title: "เล่นเกม (Gaming)", desc: "เช่น Valorant, GTA V, Elden Ring, Genshin Impact" },
  { id: "video_editing", icon: "🎬", title: "ตัดต่อวิดีโอ / กราฟิก", desc: "เช่น Premiere Pro, Photoshop, After Effects, งาน 3D" },
  { id: "office", icon: "💼", title: "ทำงานเอกสาร / เรียน", desc: "เช่น Word, Excel, ท่องเว็บ, ดูหนัง 4K, ประชุมออนไลน์" },
  { id: "ai_rendering", icon: "🤖", title: "รัน AI / โปรแกรมมิ่ง", desc: "เช่น Local LLM, Stable Diffusion, เขียนโค้ด, Docker" },
  { id: "streaming", icon: "📡", title: "สตรีมเกม / ไลฟ์สด", desc: "เช่น OBS Studio, VTuber, แคสต์เกมพร้อมไลฟ์สด" },
] as const;

const QUICK_TAGS = [
  "มี Wi-Fi ในตัว",
  "เน้นเครื่องเงียบ",
  "เคสสีขาว",
  "ขอเน้นอัปเกรดง่าย",
  "เล่น Valorant 240+ FPS",
  "ต้องการความจุ 1TB ขึ้นไป",
];

const BUDGET_PRESETS = [20000, 30000, 40000, 50000, 65000, 80000];

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

  const { register, control, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      budget: 40000,
      use_case: "gaming",
      preferred_brand: "any",
      preferred_gpu_brand: "any",
      preferred_cpu_model: "",
      preferred_gpu_model: "",
      has_existing_parts: false,
      existing_parts: [],
      question: "",
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "existing_parts" });
  const [pending, setPending] = useState<ReturnType<typeof normalize> | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error" | "done">("idle");
  const [progress, setProgress] = useState("");
  const [msg, setMsg] = useState("");
  const [res, setRes] = useState<BuildResponse | null>(null);
  const ctrl = useRef<AbortController | null>(null);
  const convId = useRef<string | undefined>(undefined);

  const curBudget = watch("budget") || 40000;
  const curUseCase = watch("use_case");
  const hasExisting = watch("has_existing_parts");
  const curQuestion = watch("question") || "";

  function addQuickTag(tag: string) {
    const trimmed = curQuestion.trim();
    if (!trimmed.includes(tag)) {
      setValue("question", trimmed ? `${trimmed}, ${tag}` : tag);
    }
  }

  function addPartByType(typeId: "cpu" | "motherboard" | "ram" | "gpu" | "psu" | "storage" | "case") {
    if (fields.length < 10) {
      append({ type: typeId, name: "", socket: "" });
    }
  }

  async function send() {
    if (!pending || state === "loading") return;
    ctrl.current?.abort();
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
          <h2>จัดสเปกคอมพิวเตอร์ในแบบของคุณ</h2>
          <p>เลือกงบประมาณและสิ่งที่ต้องการ แล้วให้ระบบวิเคราะห์จัดสเปกพร้อมเช็กความเข้ากันได้ให้อัตโนมัติ</p>
        </div>

        {/* --- Form Section --- */}
        <form className="card" onSubmit={handleSubmit((v) => setPending(normalize(v)))} noValidate>
          <h2>⚡ ความต้องการของคุณ</h2>

          {/* 1. Budget Section */}
          <div className="section-title">
            <span>1. งบประมาณที่ตั้งไว้</span>
            <small>{baht(curBudget)}</small>
          </div>
          <div className="budget-control">
            <div className="budget-input-row">
              <input
                id="budget"
                type="number"
                inputMode="numeric"
                step="1000"
                {...register("budget")}
                aria-invalid={!!errors.budget}
              />
            </div>
            <input
              type="range"
              className="budget-slider"
              min="10000"
              max="120000"
              step="1000"
              value={curBudget}
              onChange={(e) => setValue("budget", Number(e.target.value))}
              aria-label="แถบเลื่อนปรับงบประมาณ"
            />
            <div className="budget-chips">
              {BUDGET_PRESETS.map((b) => (
                <button
                  type="button"
                  key={b}
                  className={`budget-chip ${curBudget === b ? "active" : ""}`}
                  onClick={() => setValue("budget", b)}
                >
                  {baht(b)}
                </button>
              ))}
            </div>
            <div className="budget-insight">
              <span>{getBudgetInsight(curBudget)}</span>
            </div>
            {errors.budget && <p className="err" role="alert">⚠ {errors.budget.message}</p>}
          </div>

          {/* 2. Use-Case Section */}
          <div className="section-title">
            <span>2. นำไปใช้งานด้านใดเป็นหลัก?</span>
          </div>
          <div className="usecase-grid">
            {USE_CASE_CARDS.map((uc) => {
              const isSelected = curUseCase === uc.id;
              return (
                <button
                  type="button"
                  key={uc.id}
                  className={`usecase-card ${isSelected ? "active" : ""}`}
                  onClick={() => setValue("use_case", uc.id as FormValues["use_case"])}
                >
                  <span className="usecase-icon">{uc.icon}</span>
                  <div className="usecase-info">
                    <div className="usecase-title">
                      <span>{uc.title}</span>
                      <span className="usecase-check">{isSelected ? "✓" : ""}</span>
                    </div>
                    <div className="usecase-desc">{uc.desc}</div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* 3. Additional Requirements (Free Text) */}
          <div className="section-title">
            <span>3. ความต้องการเพิ่มเติม (ไม่บังคับ)</span>
          </div>
          <p className="field-hint">ระบุเกมที่เล่น หรือความชอบพิเศษ เช่น ชอบเคสขาว, เน้นเสียงเงียบ, ต้องมี Wi-Fi</p>
          <textarea
            rows={2}
            placeholder="เช่น เล่น Valorant เป็นหลัก, ต้องการ Wi-Fi ในตัว, ชอบเคสสีขาว หรือขอเน้นอัปเกรดในอนาคต"
            {...register("question")}
          />
          <div className="quick-tags">
            {QUICK_TAGS.map((tag) => (
              <button
                type="button"
                key={tag}
                className="tag-btn"
                onClick={() => addQuickTag(tag)}
              >
                + {tag}
              </button>
            ))}
          </div>

          {/* 4. Existing Parts Section */}
          <div className="section-title">
            <span>4. มีชิ้นส่วนเดิมที่อยากใช้ต่อไหม?</span>
          </div>
          <div className="segmented-control">
            <button
              type="button"
              className={`segmented-btn ${!hasExisting ? "active" : ""}`}
              onClick={() => {
                setValue("has_existing_parts", false);
              }}
            >
              ❌ ไม่มี (ประกอบใหม่หมด)
            </button>
            <button
              type="button"
              className={`segmented-btn ${hasExisting ? "active" : ""}`}
              onClick={() => {
                setValue("has_existing_parts", true);
                if (fields.length === 0) {
                  append({ type: "case", name: "", socket: "" });
                }
              }}
            >
              📦 มีชิ้นส่วนเดิม
            </button>
          </div>

          {hasExisting && (
            <div className="existing-container">
              <div className="part-picker-title">+ กดเลือกประเภทชิ้นส่วนที่มีอยู่:</div>
              <div className="part-picker-chips">
                {PART_TYPES.map((pt) => (
                  <button
                    type="button"
                    key={pt.id}
                    className="part-chip"
                    onClick={() => addPartByType(pt.id as "case" | "psu" | "storage" | "ram" | "gpu" | "motherboard" | "cpu")}
                    disabled={fields.length >= 10}
                  >
                    + {pt.label}
                  </button>
                ))}
              </div>

              {fields.length > 0 ? (
                <div className="existing-items-list">
                  {fields.map((f, i) => {
                    const currentType = watch(`existing_parts.${i}.type`);
                    const typeObj = PART_TYPES.find((t) => t.id === currentType);
                    return (
                      <div className="existing-item-card" key={f.id}>
                        <div className="existing-item-header">
                          <span className="existing-item-label">{typeObj ? typeObj.label : currentType}</span>
                          <button
                            type="button"
                            className="ghost"
                            style={{ margin: 0, padding: "2px 6px", fontSize: "12px" }}
                            onClick={() => remove(i)}
                            title="ลบชิ้นส่วนนี้"
                          >
                            × ลบ
                          </button>
                        </div>
                        <div className="existing-item-inputs">
                          <input
                            placeholder={`พิมพ์ชื่อยี่ห้อ/รุ่น เช่น ${
                              currentType === "psu" ? "Corsair CV650" :
                              currentType === "storage" ? "WD Blue SN580 1TB" :
                              currentType === "motherboard" ? "MSI B760M" :
                              currentType === "ram" ? "Kingston 16GB" :
                              currentType === "case" ? "MSI Forge M100A" : "ชื่อรุ่นที่มี"
                            }`}
                            {...register(`existing_parts.${i}.name`)}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p style={{ fontSize: "12px", color: "var(--mute)", margin: "6px 0 0" }}>
                  ยังไม่มีชิ้นส่วนที่เลือก กดปุ่มด้านบนเพื่อเพิ่ม
                </p>
              )}

              <div className="helper-callout">
                <span>💡</span>
                <span>พิมพ์เฉพาะชื่อยี่ห้อหรือรุ่นเท่าที่ทราบได้เลย (ดูจากกล่องหรือสติกเกอร์บนตัวอุปกรณ์) ระบบจะค้นหาสเปกให้เอง</span>
              </div>
            </div>
          )}

          {/* 5. Advanced Tier (Collapsible) */}
          <details className="advanced-accordion">
            <summary>⚙️ ตัวเลือกเพิ่มเติมสำหรับผู้ที่รู้เรื่องคอมพิวเตอร์ (ไม่บังคับ)</summary>
            <div className="advanced-accordion-body">
              <div className="advanced-grid">
                <div>
                  <label htmlFor="br">แบรนด์ CPU ที่ชอบ</label>
                  <select id="br" {...register("preferred_brand")}>
                    <option value="any">ไม่ระบุ (ให้ระบบเลือกความคุ้มค่า)</option>
                    <option value="intel">Intel</option>
                    <option value="amd">AMD</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="gpu-brand">แบรนด์ GPU ที่ชอบ</label>
                  <select id="gpu-brand" {...register("preferred_gpu_brand")}>
                    <option value="any">ไม่ระบุ (ให้ระบบเลือกความคุ้มค่า)</option>
                    <option value="nvidia">NVIDIA GeForce</option>
                    <option value="amd">AMD Radeon</option>
                  </select>
                </div>
              </div>
              <div className="advanced-grid" style={{ marginTop: 10 }}>
                <div>
                  <label htmlFor="cpu-model">รุ่น CPU ที่สนใจเฉพาะ</label>
                  <input id="cpu-model" placeholder="เช่น Ryzen 5 7600 หรือ i5-13400" {...register("preferred_cpu_model")} />
                </div>
                <div>
                  <label htmlFor="gpu-model">รุ่น GPU ที่สนใจเฉพาะ</label>
                  <input id="gpu-model" placeholder="เช่น RTX 4060 หรือ RX 7600" {...register("preferred_gpu_model")} />
                </div>
              </div>
            </div>
          </details>

          <button type="submit" className="submit-btn">
            🔍 ตรวจสอบและเริ่มจัดสเปก
          </button>
        </form>

        {/* --- Result & Status Section --- */}
        <section aria-live="polite">
          {pending && (
            <div className="card" style={{ marginBottom: 16 }}>
              <h2>ยืนยันความต้องการ</h2>
              <p>
                <strong>งบประมาณ:</strong> {baht(pending.budget)} · <strong>การใช้งาน:</strong> {USE_CASES[pending.use_case]}
                {pending.question && <> · <strong>เพิ่มเติม:</strong> {pending.question}</>}
                {pending.preferred_brand !== "any" && <> · <strong>CPU:</strong> {pending.preferred_brand}</>}
                {pending.preferred_gpu_brand !== "any" && <> · <strong>GPU:</strong> {pending.preferred_gpu_brand}</>}
                {pending.preferred_cpu_model && <> · <strong>รุ่น CPU:</strong> {pending.preferred_cpu_model}</>}
                {pending.preferred_gpu_model && <> · <strong>รุ่น GPU:</strong> {pending.preferred_gpu_model}</>}
                {pending.existing_parts.length > 0 && <> · <strong>ชิ้นส่วนเดิม:</strong> {pending.existing_parts.map((p) => p.name).join(", ")}</>}
              </p>
              <div style={{ display: "flex", gap: "10px", marginTop: "12px" }}>
                <button onClick={send} disabled={state === "loading"}>
                  {state === "loading" ? "กำลังประมวลผล…" : "ยืนยันและเริ่มจัดสเปก"}
                </button>
                <button type="button" className="ghost" onClick={() => setPending(null)}>
                  แก้ไขความต้องการ
                </button>
              </div>
            </div>
          )}
          {state === "idle" && !pending && (
            <div className="card">
              <h2>ยังไม่มีผลจัดสเปก</h2>
              <p>กรอกความต้องการด้านซ้ายแล้วกดปุ่ม <strong>"ตรวจสอบและเริ่มจัดสเปก"</strong> เพื่อเริ่มต้น</p>
            </div>
          )}
          {state === "loading" && <div className="card" role="status">{progress}</div>}
          {state === "error" && <div className="banner incompatible" role="alert">{msg}</div>}
          {state === "done" && res && <Result r={res} />}
        </section>

        <footer className="builder-footer" id="about">
          SPECROOM <span>·</span> วางแผนสเปกคอมในแบบของคุณ
        </footer>
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
      {r.partial_result && <div className="banner warning">ข้อมูลยังไม่ครบ: {r.degraded_services.map((item) => DEGRADED_LABELS[item] ?? item).join(", ") || "บางบริการ"}{r.degraded_services.includes("compatibility_evidence_unverified") ? "" : " ไม่พร้อมใช้งาน"}</div>}
      {r.conflicts.length > 0 && <div className="banner incompatible"><strong>ข้อขัดแย้ง</strong><ul>{r.conflicts.map((conflict) => <li key={conflict}>{conflict}</li>)}</ul>{r.suggested_fix && <p>วิธีแก้: {r.suggested_fix}</p>}</div>}
      <ul>{r.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
      {r.limitations.length > 0 && <div className="banner warning"><strong>ข้อจำกัดของข้อมูล</strong><ul>{r.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></div>}
      <table>
        <thead><tr><th>ชิ้นส่วน</th><th>รุ่นและที่มาสเปก</th><th className="n">ราคาอ้างอิง</th></tr></thead>
        <tbody>{r.parts_list.map((part) => (
          <tr key={part.type}><td>{part.type}</td><td>{part.name}
            {part.spec_source && <small className="source"><a href={part.spec_source} target="_blank" rel="noreferrer">แหล่งสเปกจากผู้ผลิต</a></small>}
            {part.price_source && <small className="source">{part.price_source}</small>}
            {!part.owned && part.store_search_links.length > 0 && (
              <small className="source">ค้นหาร้านค้า: {part.store_search_links.map((link, index) => (
                <span key={link.store}><a href={link.url} target="_blank" rel="noreferrer">{link.store}</a>{index < part.store_search_links.length - 1 ? " · " : ""}</span>
              ))}</small>
            )}</td>
            <td className="n">{part.owned ? "ใช้ชิ้นส่วนเดิม" : part.price_low !== null && part.price_high !== null
              ? `${baht(part.price_low)} – ${baht(part.price_high)}` : "ไม่มีราคาอ้างอิง"}</td></tr>))}
          <tr><th colSpan={2}>ราคารวมอ้างอิง (ไม่ใช่ใบเสนอราคา)</th><th className="n">{totalRange
            ? `${baht(totalRange.low)} – ${baht(totalRange.high)}`
            : shownTotal !== null ? baht(shownTotal) : "ประเมินไม่ได้: ราคาไม่ครบ"}</th></tr></tbody>
      </table>
      <p>ลิงก์ร้านค้าเป็นผลค้นหาสินค้าจริงจากแต่ละร้าน อาจมีราคาและสินค้าพร้อมขายแตกต่างกัน ระบบไม่รับรองราคา/สต็อกบนหน้าเหล่านั้น</p>
      {r.data_quality.price_reference_note && <p>{r.data_quality.price_reference_note}</p>}
      {r.data_quality.price_reference_observed_at && <p>ค้นหาราคาอ้างอิงเมื่อ {new Date(r.data_quality.price_reference_observed_at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}</p>}
      {r.data_quality.manufacturer_spec_sources && <details>
        <summary>ข้อมูลที่อ่านสดจากผู้ผลิต ({r.data_quality.manufacturer_spec_sources.live_pages}/{r.data_quality.manufacturer_spec_sources.requested_pages} หน้า; มีสเปกแบบ structured {r.data_quality.manufacturer_spec_sources.structured_spec_pages} หน้า)</summary>
        <p>ข้อเท็จจริงด้านความเข้ากันได้ยังมาจาก catalog ที่ตรวจทานไว้; การอ่านหน้าเว็บสดนี้ไม่แทนการยืนยัน BIOS/QVL หรือการรับรองจากผู้ผลิต</p>
        <ul>{r.data_quality.manufacturer_spec_sources.records.map((record) => (
          <li key={record.part_id}>
            {record.part_id}: {record.status === "live" ? "อ่านหน้าเว็บได้" : "อ่านหน้าเว็บไม่ได้"}
            {record.fetched_at && ` · ${new Date(record.fetched_at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}`}
            {record.source && <> · <a href={record.source} target="_blank" rel="noreferrer">แหล่งผู้ผลิต</a></>}
            {Object.keys(record.facts).length > 0 && <ul>{Object.entries(record.facts).map(([key, value]) => <li key={key}>{key}: {value}</li>)}</ul>}
          </li>
        ))}</ul>
      </details>}
      <details><summary>แหล่งข้อมูล</summary>{r.sources.length ? <ul>{r.sources.map((source) => (
        <li key={source}>{source.startsWith("https://")
          ? <a href={source} target="_blank" rel="noreferrer">{source}</a>
          : source}</li>
      ))}</ul> : "ไม่มีแหล่งข้อมูลที่ยืนยันได้"}</details>
      <p style={{ color: "var(--mute)", fontSize: ".85rem" }}>ปรับปรุงข้อมูล {new Date(r.updated_at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}</p>
    </div>
  );
}
