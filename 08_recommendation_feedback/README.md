# Module 08: Recommendation and Feedback

## หน้าที่และสถานะ

Module 02 เรียก `POST /v1/recommendation/build` เพื่อจัดรูป decision, limitations, setup steps, source references และ verified support contacts เป็น response สำหรับเว็บ. `/v1/feedback` และ `/v1/safety-queue` มี endpoint แต่ยังไม่ได้เชื่อมจากหน้าเว็บ; feedback, queue และ alert cooldown เก็บใน process memory.

ราคา/ลิงก์ null ต้องคง null. ไม่มี warranty placeholder contacts; live alerts ปิดตามค่าเริ่มต้นและยังไม่มี notification provider. `GET /health` ตรวจ service/schema.

## Endpoints

| Method | Path | หน้าที่ |
|---|---|---|
| `POST` | `/v1/recommendation/build` | format ผลแนะนำและข้อจำกัด |
| `POST` | `/v1/feedback` | รับ pseudonymized feedback; unsafe feedback ไป review queue |
| `GET` | `/v1/safety-queue` | อ่าน queue สำหรับ operator |
| `GET` | `/health` | ตรวจ service/schema |

ทุก endpoint นอกจาก health ต้องใช้ `X-Internal-Token`.

## งานเพื่อพร้อมใช้งานจริง

- แสดง source, observed/fetched/expiry timestamps, data quality และ degraded limitations ให้ครบจนถึง UI
- ต่อ feedback กับ UI โดยมี consent, abuse control, privacy notice และ retention policy ก่อนเก็บข้อมูล
- ย้าย queue/cooldown/feedback ไป persistent store ที่ควบคุม access, audit และ retention
- เพิ่ม alerts เฉพาะ provider ที่ได้รับอนุญาตและผู้ใช้ consent; ใช้ verified support contact directory ที่มี source/version

## ตั้งค่าและรัน

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8600 --reload
python -m pytest -q
```

ภาพรวมระบบและเกณฑ์ real-data readiness ดู [root README](../README.md); วิธีเปิดทุก service ดู [README_RUN.md](../README_RUN.md).
