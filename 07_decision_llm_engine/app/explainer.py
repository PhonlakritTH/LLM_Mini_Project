"""Generate an evidence-grounded explanation without allowing the LLM to change a decision."""
import json
import re

import httpx
from jsonschema import ValidationError, validate

from .config import settings
from .models import ActionCode

# ---------- fallback templates (used when LLM is unavailable) ----------
FALLBACK_TEMPLATES: dict[str, dict] = {
    "FINALIZE_BUILD": {
        "summary": "ชุดสเปกนี้ลงตัวและอยู่ในงบประมาณที่ตั้งไว้ พร้อมสำหรับการประกอบใช้งานได้ทันที",
        "reasons": [
            "ชิ้นส่วนทุกชิ้นผ่านการตรวจสอบความเข้ากันได้ 100% (Socket, RAM, กำลังไฟ PSU)",
            "ประสิทธิภาพเหมาะสมกับลักษณะการใช้งานที่เลือก รองรับการเล่นเกมและทำงานได้อย่างลื่นไหล",
            "ราคารวมอ้างอิงอยู่ในกรอบงบประมาณที่กำหนด",
        ],
        "immediate_actions": ["ตรวจสอบสต็อกสินค้าและราคาโปรโมชันหน้าร้านค้าจริงก่อนสั่งซื้อ"],
    },
    "SWAP_COMPONENT": {
        "summary": "ชุดสเปกใกล้เคียงความต้องการ แต่แนะนำให้ปรับเปลี่ยนชิ้นส่วนบางชิ้นเพื่อให้ลงตัวยิ่งขึ้น",
        "reasons": ["มีชิ้นส่วนทางเลือกที่คุ้มค่ากว่าหรือช่วยให้อยู่ในงบประมาณ"],
        "immediate_actions": ["ตรวจสอบชิ้นส่วนทางเลือกที่ระบบแนะนำ"],
    },
    "RECONFIGURE_BUILD": {
        "summary": "ราคารวมของชุดสเปกนี้เกินงบประมาณที่ตั้งไว้เล็กน้อย แนะนำให้ปรับลดบางชิ้นหรือเพิ่มงบ",
        "reasons": ["ราคารวมในตลาดปัจจุบันสูงกว่างบประมาณที่ระบุ"],
        "immediate_actions": ["ลดระดับการ์ดจอ/ซีพียูลงหนึ่งระดับ หรือเพิ่มงบประมาณ"],
    },
    "NEEDS_PRICE_DATA": {
        "summary": "ยังไม่พบราคาตลาดล่าสุดของบางชิ้นส่วน แนะนำตรวจสอบราคาเพิ่มเติมจากหน้าร้าน",
        "reasons": ["ระบบค้นหาราคาอ้างอิงในไทยได้ไม่ครบทุกชิ้นส่วน"],
        "immediate_actions": ["ตรวจสอบราคาชิ้นส่วนที่ขาดไปจากร้านค้าออนไลน์หรือหน้าร้านจริง"],
    },
    "NEEDS_REVIEW": {
        "summary": "ชุดสเปกนี้ใช้งานได้ดี แต่อาจมีช่วงราคาที่คาบเกี่ยวกับงบ หรือควรตรวจสอบรายละเอียดกับร้านค้าก่อนซื้อ",
        "reasons": ["ราคาตลาดของบางชิ้นส่วนมีช่วงราคาขึ้นลงตามร้านค้าและโปรโมชัน"],
        "immediate_actions": ["ตรวจสอบราคาล่าสุดและของแถมจากร้านค้าที่คุณสะดวกซื้อ"],
    },
    "AVOID_COMBINATION": {
        "summary": "ชิ้นส่วนชุดนี้ไม่สามารถประกอบร่วมกันได้โดยตรง เนื่องจากสเปกทางเทคนิคไม่ตรงกัน",
        "reasons": ["ตรวจพบจุดที่ไม่เข้ากัน เช่น ซ็อกเก็ต CPU และเมนบอร์ดไม่ตรงกัน"],
        "immediate_actions": ["เลือกเมนบอร์ดและ CPU ที่ใช้ Socket เดียวกัน"],
    },
}

SCHEMA = {
    "type": "object",
    "required": ["summary", "reasons", "immediate_actions"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "maxLength": 400},
        "reasons": {"type": "array", "items": {"type": "string", "maxLength": 400}, "maxItems": 6},
        "immediate_actions": {"type": "array", "items": {"type": "string", "maxLength": 400}, "maxItems": 4},
    },
}


class LLMProviderError(Exception):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def build_prompt(action: ActionCode, evidence: dict) -> str:
    safe_evidence = json.dumps(evidence, ensure_ascii=False)[: settings.max_input_tokens * 3]
    return json.dumps({"locked_action": action, "evidence": safe_evidence}, ensure_ascii=False)


def _fallback_explanation(action: str) -> dict:
    """Return a pre-built template explanation when LLM is unavailable."""
    tmpl = FALLBACK_TEMPLATES.get(action, FALLBACK_TEMPLATES["NEEDS_REVIEW"])
    return dict(tmpl)  # shallow copy


async def call_llm(prompt: str) -> dict:
    if not settings.llm_api_key:
        raise LLMProviderError("LLM_API_KEY is not configured.", status_code=503)

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.llm_model_explainer,
        "temperature": settings.temperature,
        "max_tokens": settings.max_output_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a friendly, expert PC hardware advisor. "
                    "Explain the supplied locked action using only the supplied evidence in natural, friendly Thai language. "
                    "Include realistic everyday performance insights (e.g. gaming FPS estimates, video editing/work capability) "
                    "and explain clearly why this build fits their use case and budget. "
                    "Avoid overly dense jargon; explain terms simply. "
                    "Never alter the locked action, invent ungrounded component names, or contradict the evidence. "
                    "Return a JSON object with: summary (Thai string), reasons (array of Thai strings), and immediate_actions (array of Thai strings)."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        if status == 401:
            message = "LLM provider rejected the API key (HTTP 401). Verify LLM_API_KEY."
        elif status == 403:
            message = "LLM provider denied access (HTTP 403). Check project permissions, model access, and billing."
        elif status == 404:
            message = "LLM endpoint or model was not found (HTTP 404). Check LLM_BASE_URL and LLM_MODEL_EXPLAINER."
        elif status == 429:
            message = "LLM provider quota or rate limit exceeded (HTTP 429)."
        else:
            message = f"LLM provider request failed (HTTP {status}). Check provider status and configuration."
        raise LLMProviderError(message, status_code=503) from error
    except httpx.HTTPError as error:
        raise LLMProviderError(f"LLM provider connection failed: {error}", status_code=503) from error

    try:
        content = response.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
        validate(result, SCHEMA)
        return result
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as error:
        raise LLMProviderError("LLM provider returned an invalid structured explanation.", status_code=502) from error


def validate_and_lock(raw: dict, reasons_in: list[str],
                      wattage_warning: str | None) -> tuple[dict, bool, bool]:
    validate(raw, SCHEMA)
    for reason in raw["reasons"]:
        if re.search(r"https?://|<script", reason, re.I):
            raise ValidationError("unsafe content in reasons")
    raw["reasons"] = list(dict.fromkeys(reasons_in + raw["reasons"]))[:6]
    if wattage_warning and wattage_warning not in raw["immediate_actions"]:
        raw["immediate_actions"] = [wattage_warning, *raw["immediate_actions"]][:4]
    return raw, True, False
