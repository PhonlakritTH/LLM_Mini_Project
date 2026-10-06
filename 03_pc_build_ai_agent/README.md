# Module 03: PC Build AI Agent

## หน้าที่และข้อมูลรุ่น

FastAPI service จัดชุดสเปกจาก SQLite knowledge database (`data/components.sqlite3`) ที่ seed/refresh จาก [`data/components.json`](data/components.json); `app/knowledge_base.py` ดูแล schema, index และ queries. Records มีชื่อรุ่น, specs, search terms สำหรับลด false match และ URL แหล่งผู้ผลิต. เลือก candidate ตามงบ, use case, brand/model ที่ขอ และเลือกชุดที่ช่วงราคาอ้างอิงครบและอยู่ในงบเมื่อมีข้อมูลเพียงพอ. รุ่นนอกฐานความรู้จะไม่ถูกสร้างขึ้นเอง.

รายการ compatibility ยังเป็น curated dataset เริ่มต้น 13 รุ่น/รายการ ไม่ได้ถูกเขียนทับจากเว็บโดยอัตโนมัติ. ทุกคำขอจะพยายามดึง metadata/structured facts สดจากหน้า manufacturer URL ของชิ้นส่วนที่เลือก และคืน URL, เวลาที่ดึง, fields ที่อ่านได้; หน้าที่บล็อกการดึงหรือไม่มี facts จะทำเครื่องหมาย degraded. ข้อมูล socket, compatibility list, BIOS version และ RAM QVL ยังคงต้อง audit/ยืนยันจากเอกสารผู้ผลิต; URL หรือ metadata สดไม่ใช่หลักฐานว่ารุ่นย่อยหรือ BIOS เฉพาะตัวผ่านแล้ว. SQLite file สร้าง/refresh จาก JSON เมื่อ service เริ่ม; แก้/เพิ่ม knowledge โดยอัปเดต JSON seed และ restart service.

Flow: `classify -> extract -> ask_missing -> knowledge_base -> price_reference -> integrate -> manufacturer_specs -> compatibility -> quality -> package`. เรียก Module 04 เฉพาะ `price`; ไม่เรียก stock หรือ benchmark.

## Endpoints และการรัน

- `POST /v1/agent/run` ใช้ `X-Internal-Token`; รับงบ/brand/model และคืนสเปก, price range, provenance และข้อจำกัด
- `GET /health`

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8100 --reload
python -m pytest -q
```

ตั้ง `PRICE_SERVICE_URL=http://localhost:8200` และ `INTERNAL_TOKEN` ให้ตรงกับ Modules 02/04. Module 04 ต้องมี `SERPAPI_API_KEY` เพื่อหาช่วงราคา. Query ราคาครอบคลุม candidate ที่กำลังเปรียบเทียบและอาจใช้ API quota ตามจำนวนรุ่น; cache ลดการ query ซ้ำช่วงสั้น.

หากไม่มีราคาครบจะส่ง `total_price_range=null` และระบุ `budget_fit=unknown`; ห้ามใช้เป็นการยืนยันงบ. รายละเอียดการรัน: [README_RUN.md](../README_RUN.md).
