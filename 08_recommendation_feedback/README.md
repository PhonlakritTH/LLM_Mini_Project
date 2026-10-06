# Module 08: Recommendation and Feedback

## หน้าที่และสถานะ

จัดรูปผลลัพธ์สำหรับ Module 01 ให้มี parts, ช่วงราคาอ้างอิง, source/timestamp, action และ limitations. ไม่มี stock status, retailer URL, checkout หรือ purchase action. ราคาไม่ครบ/compatibility needs-review ต้องอยู่ในข้อความผลลัพธ์ ไม่ถูกซ่อนหรือแปลงเป็น 0.

`POST /v1/feedback` และ `/v1/safety-queue` ยังเป็น internal endpoints ที่ยังไม่เชื่อมหน้าเว็บ; feedback/queue และ alert cooldown อยู่ใน process memory. Notifications/live alerts ปิดไว้.

## Endpoints และการรัน

| Method | Path | หน้าที่ |
|---|---|---|
| `POST` | `/v1/recommendation/build` | สร้างผลสำหรับ UI |
| `POST` | `/v1/feedback` | รับ internal feedback |
| `GET` | `/v1/safety-queue` | อ่าน safety queue |
| `GET` | `/health` | ตรวจ service/schema |

ทุก endpoint นอกจาก health ใช้ `X-Internal-Token`.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8600 --reload
python -m pytest -q
```

ก่อนเปิด public ให้กำหนด consent/privacy/retention และ persistent storage สำหรับ feedback. วิธีรันทั้งระบบ: [README_RUN.md](../README_RUN.md).
