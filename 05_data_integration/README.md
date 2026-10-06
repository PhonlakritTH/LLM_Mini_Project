# Module 05: Data Integration

## หน้าที่และสถานะ

รับ requested parts กับ normalized provider records ที่ Module 02 ส่งต่อมาจาก Module 03/04 แล้วสร้าง canonical snapshot ต่อ request. โมดูลนี้ไม่ได้เรียก provider เอง ไม่เก็บ catalog ถาวร และไม่มี scheduled ingestion.

`POST /v1/integration/snapshot` ต้องมี `X-Internal-Token`; `GET /health` แสดง schema version. Pipeline ตรวจ schema, quarantine invalid records, ลบ exact duplicates, รวม price/stock/benchmark/spec, เก็บ source lineage และ flag missing/stale/conflicting/out-of-stock. Requested parts ยังคงอยู่ใน snapshot เมื่อไม่มี record; price/stock ที่ขาดเป็น null. Owned parts แยกจากรายการซื้อ.

## ใช้ข้อมูลจริงอย่างไร

- Module 04 เป็นผู้สร้าง provider records; ต้องคง `source`, canonical product ID, `observed_at`, `fetched_at`/`expires_at`, currency/units และ authority
- ตรวจ timestamp และหน่วยก่อนรวม; อย่าแก้ conflict ด้วยการเลือกค่าที่ดูดีที่สุดโดยไม่เปิดเผย rule/source
- ความครบถ้วนของ snapshot ไม่เท่ากับความถูกต้องของ source; caller ต้องพิจารณา data-quality flags และ freshness
- ปัจจุบัน snapshot เป็น in-memory/request-scoped response; ห้ามใช้เป็น authoritative catalog หรืออ้างว่าสามารถค้นย้อนหลังได้

งานถัดไป: กำหนด canonical schema/units, เพิ่ม migration/version policy, persisted catalog/snapshot และ retention/access controls เมื่อมีข้อกำหนด storage ที่ชัดเจน. เพิ่ม test clock abstraction เพื่อทดสอบ freshness อย่าง deterministic.

## ตั้งค่าและรัน

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8300 --reload
python -m pytest -q
```

อ่าน [root README](../README.md) สำหรับแผนระบบจริง และ [README_RUN.md](../README_RUN.md) สำหรับการเปิดทุก service.
