# Module 03: PC Build AI Agent

## หน้าที่และข้อมูลรุ่น

FastAPI service จัดชุดสเปกจาก SQLite knowledge database (`data/components.sqlite3`) ที่ seed/refresh จาก [`data/components.json`](data/components.json); `app/knowledge_base.py` ดูแล schema, index และ queries. Records มีชื่อรุ่น, specs, search terms สำหรับลด false match และ URL แหล่งผู้ผลิต. เลือก candidate ตามงบ, use case, brand/model ที่ขอ และเลือกชุดที่ช่วงราคาอ้างอิงครบและอยู่ในงบเมื่อมีข้อมูลเพียงพอ. รุ่นนอกฐานความรู้จะไม่ถูกสร้างขึ้นเอง.

รายการความรู้ยังเป็น curated dataset เริ่มต้น 13 รุ่น/รายการ ไม่ได้ sync จากผู้ผลิตอัตโนมัติ; URL เป็นแหล่งอ้างอิงแต่ dataset ยังต้องได้รับการ audit และเพิ่ม version/change review ก่อนใช้ตัดสินใจประกอบจริง. CPU support list, BIOS version และ RAM QVL ระบุ not-verified จึงถูกส่งให้ Module 06 แจ้งเป็น needs-review. SQLite file สร้าง/refresh จาก JSON เมื่อ service เริ่ม; แก้/เพิ่ม knowledge โดยอัปเดต JSON seed และ restart service.

Flow: `classify -> extract -> ask_missing -> knowledge_base -> price_reference -> integrate -> compatibility -> quality -> package`. เรียก Module 04 เฉพาะ `price`; ไม่เรียก stock หรือ benchmark.

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
