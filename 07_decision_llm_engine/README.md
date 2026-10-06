# Module 07: Decision and LLM Engine

## หน้าที่

รับช่วงราคาอ้างอิง, compatibility และ data quality เพื่อเลือก deterministic action. Compatibility conflict เป็น hard stop; build ที่มีข้อมูล compatibility ไม่พอจะไม่ถูก finalize; งบจะถือว่าผ่านเฉพาะเมื่อช่วงราคาทั้งช่วงไม่เกิน budget. ช่วงราคาที่คร่อม budget หรือข้อมูลหายจะส่ง `NEEDS_PRICE_DATA`; build เกินงบจะส่ง `RECONFIGURE_BUILD`.

LLM ไม่ได้ถูกเรียกจริงใน mini project; fixed template อธิบายผลที่ rules ตัดสินไว้ และไม่มีสิทธิ์เปลี่ยน action/ราคา/compatibility. ไม่มี stock/trend logic หรือการอนุมัติซื้อ.

## API และการรัน

`POST /v1/decision/evaluate` ใช้ `X-Internal-Token`; `GET /health` แสดง policy version.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8500 --reload
python -m pytest -q
```

ก่อนต่อ LLM provider ต้องคง action locking, structured-output validation, timeout/cost controls และ citations. API key ที่ตั้งอยู่ปัจจุบันยังไม่ทำให้เกิด live LLM call. ดู flow ที่ [root README](../README.md).
