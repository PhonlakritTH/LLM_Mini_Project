# Module 06: Compatibility and Knowledge Services

## หน้าที่และสถานะ

รับ Module 05 snapshot จาก Module 02 และประเมิน compatibility พร้อม evidence/alternatives. กฎ deterministic ที่มีอยู่ตรวจ socket CPU/board, headroom PSU, wattage limit และ case form factor บางกรณี. ไม่ครอบคลุม compatibility matrix เต็ม เช่น CPU BIOS support, RAM generation/QVL, GPU clearance, PSU connectors หรือ radiator fit; ข้อมูลที่ไม่พอควรเป็น needs-review ไม่ใช่ compatible ที่ยืนยันแล้ว.

`POST /v1/knowledge/assess` ต้องมี `X-Internal-Token`; `GET /health` รายงาน versions. ค่า `ENABLE_SAMPLE_KNOWLEDGE` ปิดเป็นค่าเริ่มต้น. Default request ไม่คืน sample passages/ราคา alternatives; RAG และ alternative providers ยังไม่มี live implementation และผลจะระบุ degraded.

## ก่อนเปิดใช้ข้อมูลความเข้ากันได้จริง

1. เลือก official/manufacturer sources และสิทธิ์ใช้เอกสาร; เก็บ document URL/ID, section, revision/date และ source lineage
2. สร้าง versioned compatibility facts/catalog (socket, chipset, CPU support/BIOS, memory type, form factor, clearance, PSU connectors/wattage) พร้อม unit normalization
3. ใช้ deterministic rules เป็น safety gate; ข้อมูลที่ไม่มีหลักฐานต้องคืน unknown/needs-review
4. ทำ RAG จากเอกสารที่ตรวจสอบสิทธิ์/รุ่นและอ้าง citation ตรงกับข้อความ; retrieval ช่วยอธิบาย ไม่เป็นแหล่งตัดสิน compatibility เพียงอย่างเดียว
5. สร้าง alternatives จาก catalog และ offers ที่ตรงรุ่น/compatibility/ราคา freshness ไม่ใช้รายการราคาฝังใน source code

## ตั้งค่าและรัน

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8400 --reload
python -m pytest -q
```

เปิด sample mode ไม่ได้ทำให้ข้อมูลกลายเป็นข้อมูลจริง; ห้ามเปิดใน production. แผน end-to-end และ real-data requirements อยู่ใน [root README](../README.md).
