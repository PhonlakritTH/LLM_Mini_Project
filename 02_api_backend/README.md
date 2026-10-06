# Module 02: API Backend

## หน้าที่และสถานะ

FastAPI gateway ระหว่างเว็บกับ modules ภายใน: ตรวจ JWT สำหรับ request จากเว็บ, rate limit, เรียก Module 03, แล้ว orchestrate Modules 05–08 ตามลำดับและแปลงผลเป็น web response schema. Module 04 ถูกเรียกจาก tools ใน Module 03; Module 05 ไม่ได้เรียก provider เอง.

สถานะ auth/rate-limit/idempotency เป็น development/in-process memory; `/v1/auth/dev-token` เป็น endpoint DEV ONLY. ยังไม่พร้อมเปิด public โดยไม่มีการเปลี่ยน authentication, secret, persistence, quotas และ monitoring.

## Endpoints

| Method | Path | หน้าที่ |
|---|---|---|
| `POST` | `/v1/auth/dev-token` | ออก short-lived development JWT; ห้ามใช้เป็น production login |
| `POST` | `/v1/builder/recommendations` | รับคำขอแล้วเรียก Module 03 และ Modules 05–08 |
| `GET` | `/health`, `/ready` | ตรวจ process/readiness |

เมื่อ Module 03 เข้าไม่ถึงจะคืน 503; เมื่อ downstream ล้มเหลวระบบสร้างผล degraded และไม่ควรตีความเป็นคำแนะนำที่ตรวจครบแล้ว. Module 03 เองยังเลือก candidate จากรายการคงที่; Module 02 ไม่สามารถยืนยัน candidate เหล่านี้กับ catalog สินค้าจริงในปัจจุบัน. ราคาหรือ stock ที่หายต้องคง unknown.

## การไหลที่ orchestrate

`02 -> 03 -> 04 -> 02 -> 05 -> 06 -> 07 -> 08 -> 01`

Module 02 ส่ง candidate และ evidence จาก agent ไป Module 05; ส่ง snapshot ไปตรวจ compatibility ที่ Module 06; ส่งผลกฎไป Module 07; แล้วจัดรูปแบบคำตอบผ่าน Module 08. เก็บ source/freshness/ข้อผิดพลาดไว้ในผลตอบกลับให้มากพอสำหรับหน้าเว็บ ไม่เปลี่ยน missing เป็นค่า default ที่ดูเหมือนผ่าน validation.

## ตั้งค่าและรัน

คัดลอก `.env.example` เป็น `.env` ในโฟลเดอร์นี้. ตั้ง URLs ของ Modules 03 และ 05–08 ตาม local ports ใน root [README_RUN.md](../README_RUN.md); ตั้ง `INTERNAL_TOKEN` ให้ตรงกับ Modules 03/04.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
python -m pytest -q
```

## งานก่อน production / real data

- ใช้ OIDC/OAuth2 provider แทน development-token endpoint; เก็บ signing/internal secrets ใน secret manager
- ย้าย rate limit, idempotency, tracing และ feedback-related state ออกจาก process memory
- กำหนด timeout/retry/partial-response policy ต่อ downstream และเก็บ source/freshness ใน final schema
- ทำ integration tests กับ provider fixture และ live tests ที่เปิดเมื่อกำหนด credentials โดยชัดเจน

ทดสอบ end-to-end และดูสถานะข้อมูลจริงได้ตาม root [README.md](../README.md) และ [README_RUN.md](../README_RUN.md).
