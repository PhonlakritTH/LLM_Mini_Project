import { z } from "zod";
export const USE_CASES = { gaming: "Gaming", video_editing: "Video editing", office: "Office", streaming: "Streaming", ai_rendering: "AI / rendering" } as const;
export const PART_TYPES = ["cpu", "motherboard", "ram", "gpu", "psu", "storage", "case"] as const;

export const formSchema = z.object({
  budget: z.coerce.number({ invalid_type_error: "Enter a number" }).int().min(8000, "Minimum 8,000 THB").max(500000, "Maximum 500,000 THB"),
  use_case: z.enum(["gaming", "video_editing", "office", "streaming", "ai_rendering"]),
  preferred_brand: z.enum(["any", "intel", "amd", "nvidia"]),
  existing_parts: z.array(z.object({
    type: z.enum(PART_TYPES),
    name: z.string().trim().min(1, "Name required").max(80),
    socket: z.string().trim().max(20).optional(),
  })).max(10),
  question: z.string().max(500),
});
export type FormValues = z.infer<typeof formSchema>;

/** Normalize tags/units before sending (step 3). Decisions stay on the server. */
export function normalize(v: FormValues) {
  return {
    ...v,
    question: v.question.trim(),
    existing_parts: v.existing_parts.map((p) => ({ ...p, socket: p.socket ? p.socket.toUpperCase().replace(/\s+/g, "") : undefined })),
  };
}
