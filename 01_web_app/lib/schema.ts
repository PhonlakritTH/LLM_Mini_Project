import { z } from "zod";
export const USE_CASES = {
  gaming: "เล่นเกม (Gaming)",
  video_editing: "ตัดต่อวิดีโอ / กราฟิก (Video & Graphics)",
  office: "ทำงานเอกสาร / เรียน (Office & Study)",
  streaming: "สตรีมเกม / ไลฟ์สด (Streaming)",
  ai_rendering: "รัน AI / โปรแกรมมิ่ง (AI & Dev)",
} as const;

export const PART_TYPES = [
  { id: "case", label: "เคส (Case)" },
  { id: "psu", label: "พาวเวอร์ซัพพลาย (PSU)" },
  { id: "storage", label: "SSD / ฮาร์ดดิสก์ (Storage)" },
  { id: "ram", label: "แรม (RAM)" },
  { id: "gpu", label: "การ์ดจอ (GPU)" },
  { id: "motherboard", label: "เมนบอร์ด (Mainboard)" },
  { id: "cpu", label: "ซีพียู (CPU)" },
] as const;

export const formSchema = z.object({
  budget: z.coerce.number({ invalid_type_error: "กรุณาระบุงบประมาณเป็นตัวเลข" }).int().min(8000, "งบขั้นต่ำ 8,000 บาท").max(500000, "งบสูงสุด 500,000 บาท"),
  use_case: z.enum(["gaming", "video_editing", "office", "streaming", "ai_rendering"]),
  preferred_brand: z.enum(["any", "intel", "amd", "nvidia"]).default("any"),
  preferred_gpu_brand: z.enum(["any", "amd", "nvidia"]).default("any"),
  preferred_cpu_model: z.string().trim().max(100).default(""),
  preferred_gpu_model: z.string().trim().max(100).default(""),
  has_existing_parts: z.boolean().default(false),
  existing_parts: z.array(z.object({
    type: z.enum(["cpu", "motherboard", "ram", "gpu", "psu", "storage", "case"]),
    name: z.string().trim().max(80),
    socket: z.string().trim().max(20).optional().default(""),
    wattage: z.preprocess((value) => value === "" || value == null ? undefined : Number(value),
      z.number().int().min(100).max(2000).optional()),
  })).max(10).default([]),
  question: z.string().max(500).optional().default(""),
});
export type FormValues = z.infer<typeof formSchema>;

/** Normalize tags/units before sending (step 3). Decisions stay on the server. */
export function normalize(v: FormValues) {
  const parts = v.has_existing_parts
    ? v.existing_parts
        .filter((p) => p.name.trim().length > 0)
        .map((p) => ({
          ...p,
          name: p.name.trim() || `ชิ้นส่วนเดิม (${p.type})`,
          socket: p.socket ? p.socket.toUpperCase().replace(/\s+/g, "") : undefined,
        }))
    : [];

  return {
    budget: v.budget,
    use_case: v.use_case,
    preferred_brand: v.preferred_brand || "any",
    preferred_gpu_brand: v.preferred_gpu_brand || "any",
    preferred_cpu_model: (v.preferred_cpu_model || "").trim(),
    preferred_gpu_model: (v.preferred_gpu_model || "").trim(),
    existing_parts: parts,
    question: (v.question || "").trim(),
  };
}

