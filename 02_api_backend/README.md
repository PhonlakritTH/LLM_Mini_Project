# Module 02: API Backend

## หน้าที่

FastAPI gateway รับคำขอจาก Module 01, เรียก Module 03 เพื่อจัดชุด candidate จากข้อมูลรุ่นที่มีแหล่งอ้างอิง แล้วส่งข้อมูลราคา/สเปกผ่าน Modules 05–08 ก่อนจัด response สำหรับหน้าเว็บ. ไม่มี stock, checkout หรือ order flow.

`POST /v1/builder/recommendations` รับงบ, use case, CPU/GPU brand/model preferences, existing parts และ question. ค่าราคา `null` คงเป็น unknown; backend ไม่เติมศูนย์แทนข้อมูลที่ขาด และไม่ส่งผลว่าจัดได้ในงบเมื่อช่วงราคายังไม่ครบ. แต่ละ part มีลิงก์ค้นหาไปยัง BaNANA/Amazon ที่สร้างจากชื่อรุ่น ไม่มี API หรือราคา/stock สมมติ; ผู้ใช้ต้องตรวจสอบ offer ที่ตรงรุ่นบนเว็บร้านเอง.

## Endpoints และการรัน

| Method | Path | หน้าที่ |
|---|---|---|
| `POST` | `/v1/auth/dev-token` | ออก JWT สำหรับ development เท่านั้น |
| `POST` | `/v1/builder/recommendations` | จัดสเปกและรวมผล modules |
| `GET` | `/health`, `/ready` | ตรวจ service |

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
python -m pytest -q
```

## ข้อจำกัด/ก่อน production

auth, rate limit และ idempotency ยังเก็บใน memory; dev-token ไม่ใช่ login production. Module 03/04 ต้องใช้ `INTERNAL_TOKEN` เดียวกัน. ผลราคาเป็นประมาณการที่ต้องมี `SERPAPI_API_KEY`; ไม่มี key หรือ matching ไม่ครบจะได้ degraded output.

ก่อนเปิด public ต้องเปลี่ยนเป็น OIDC/OAuth2, secret management, persistent rate limit/idempotency, observability และกำหนด privacy/retention. วิธีรันครบระบบ: [README_RUN.md](../README_RUN.md).
