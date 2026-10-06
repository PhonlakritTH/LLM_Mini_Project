# Module 07: Decision and LLM Engine

## หน้าที่

รับช่วงราคาอ้างอิง, compatibility และ data quality เพื่อเลือก deterministic action. Compatibility conflict เป็น hard stop; build ที่มีข้อมูล compatibility ไม่พอจะไม่ถูก finalize; งบจะถือว่าผ่านเฉพาะเมื่อช่วงราคาทั้งช่วงไม่เกิน budget. ราคาที่ขาดจะส่ง `NEEDS_PRICE_DATA`; ช่วงราคาที่คร่อม budget หรือ compatibility ที่ต้องตรวจเพิ่มจะส่ง `NEEDS_REVIEW`; build ที่ยืนยันได้ว่าเกินงบจะส่ง `RECONFIGURE_BUILD`.

rules จะตัดสิน action ก่อน แล้วเรียก chat-completions API แบบ OpenAI-compatible เพื่อเขียนคำอธิบายเป็น JSON; LLM ไม่มีสิทธิ์เปลี่ยน action/ราคา/compatibility. ต้องตั้ง `LLM_API_KEY`, `LLM_BASE_URL` และ `LLM_MODEL_EXPLAINER`; หาก key หาย, provider ล้มเหลว หรือ JSON ไม่ผ่าน schema ระบบคืน HTTP error และไม่ส่งคำอธิบาย template แทน. ตั้งค่าผ่าน root `.env` เมื่อใช้ Docker หรือ `07_decision_llm_engine/.env` เมื่อต้องการรัน local. ไม่ส่ง API key ไป frontend.

## API และการรัน

`POST /v1/decision/evaluate` ใช้ `X-Internal-Token`; `GET /health` แสดง policy version.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8500 --reload
python -m pytest -q
```

ส่งหลักฐาน compatibility, alternatives และเหตุผลที่ rules สร้างให้ LLM; ใช้ `response_format=json_object`, จำกัด output และตรวจ schema ก่อนตอบ. ราคา/ตัวเลขต้องมาจาก evidence เท่านั้น. ดู flow ที่ [root README](../README.md).
