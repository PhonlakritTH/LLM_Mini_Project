# Module 05: Data Integration

## หน้าที่

รวมเฉพาะชิ้นส่วนในชุดที่ Module 03 เลือกแล้ว พร้อม curated manufacturer specification facts และ normalized price-reference records จาก Module 04 เป็น snapshot ต่อ request. Price records ของ candidate ทางเลือกยังใช้ประกอบการเลือกใน Module 03 แต่จะไม่ถูกเพิ่มเข้าชุดผลลัพธ์ที่ส่งให้ผู้ใช้. เก็บ price range, timestamps, source lineage, coverage, freshness และ flags. ไม่มี scheduled ingestion หรือ persistent parts database; คำว่า snapshot/catalog ใน API หมายถึงข้อมูลของคำขอนี้ ไม่ใช่หน้าร้านหรือฐานข้อมูลจัดซื้อ.

Missing prices remain `null`; existing owned parts are not assigned a fake zero price. ราคาที่ขาดทำให้ coverage ต่ำ/degraded และไม่รวมเป็นยอดราคาเต็ม.

## API และการรัน

- `POST /v1/integration/snapshot` ใช้ `X-Internal-Token`
- `GET /health` แสดง schema version

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8300 --reload
python -m pytest -q
```

Module นี้ไม่ได้เรียก provider เอง; ต้องส่ง provenance/spec sources จาก Module 03 และ timestamps/source ของราคา Module 04. Snapshot อยู่ใน memory/request response ไม่ใช่ข้อมูลค้นย้อนหลัง. ดู flow ที่ [root README](../README.md).
