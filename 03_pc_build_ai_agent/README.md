# Module 03: PC Build AI Agent

## หน้าที่และสถานะ

FastAPI service สำหรับรับคำขอจาก Module 02 และรันกราฟ deterministic ที่จำกัดจำนวน step/tool call. กราฟปัจจุบันคือ:

`classify -> extract -> ask_missing -> plan -> fetch -> integrate -> compatibility -> alternatives_rag -> quality -> package`

`plan` ยังใช้ตาราง CPU/GPU/board และค่าชิ้นส่วนที่ระบุไว้ใน `app/graph.py` โดยตรง ไม่ได้อ่าน catalog สินค้าหรือราคาเพื่อสร้าง candidate. ชื่อสินค้าจึงเป็น candidate สำหรับทดสอบ flow ไม่ใช่ catalog ที่ยืนยัน stock/offer ได้. Empty provider URL ทำให้ tool ล้มเหลวและผล degraded; ไม่มี fallback ราคาปลอม.

## ข้อมูลและ endpoints

- `POST /v1/agent/run` ต้องมี `X-Internal-Token`; คืน evidence package, degraded services, trace และ request IDs
- `GET /health` คืนสถานะและ policy/prompt versions
- tools ส่ง candidate names ไป Module 04 เพื่อค้น price/stock/benchmark; normalized records ถูกส่งกลับไปให้ Module 02 แล้วต่อ Module 05
- compatibility ที่ agent ทำเองเป็น checks ขั้นต้น; Module 06 เป็น compatibility stage ใน backend orchestration

## ทำให้ candidate เป็นสินค้าจริง

1. สร้าง/นำเข้า catalog ที่มี canonical `part_id`, exact product name, manufacturer part number, category และ verified specs/source/version
2. เปลี่ยนตาราง candidate ใน `graph.py` ให้ query catalog ตามงบ/use case/brand และตัด candidate ที่ข้อมูล required หายออกหรือส่งให้ review
3. ใช้ canonical ID เดียวกันกับ Module 04 และ Module 05; ห้าม map ราคาด้วยข้อความชื่อรุ่นแบบ fuzzy โดยไม่มี match score/การตรวจ
4. จัด budget จากราคา offers ที่สดจริง; ถ้าราคาขาดอย่าคำนวณยอดรวมเป็นราคาครบ และส่งสถานะ unknown/degraded ต่อไป
5. เพิ่ม tests ที่ใช้ fixture แยกจาก runtime และ provider tests ที่ validate match/source/freshness.

LLM settings ที่มีอยู่ไม่ได้ทำให้ candidate หรือราคาเป็นข้อมูลจริง. ต้องคงกฎที่ป้องกัน URL/SQL/tool misuse และไม่ให้ LLM กำหนดราคาเอง.

## ตั้งค่าและรัน

คัดลอก `.env.example` เป็น `.env`; ตั้ง `PRICE_SERVICE_URL`, `STOCK_SERVICE_URL`, `BENCHMARK_SERVICE_URL` เป็น Module 04 (เช่น `http://localhost:8200`) และใช้ `INTERNAL_TOKEN` เดียวกับ Modules 02/04.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8100 --reload
python -m pytest -q
```

ตั้งค่าการรันระบบครบตาม root [README_RUN.md](../README_RUN.md). แผน real-data ของระบบอยู่ที่ root [README.md](../README.md).
