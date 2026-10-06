# AI PC Spec Builder

ระบบช่วยวางแผนสเปกคอมตามงบ การใช้งาน ยี่ห้อ/รุ่นที่สนใจ พร้อมตรวจ compatibility และแสดงราคาอ้างอิงเป็นช่วง ระบบนี้ **ไม่ใช่ร้านค้า**: ไม่มี stock, checkout, order หรือคำแนะนำให้ซื้อจากร้านใด

## ข้อมูลที่ใช้และข้อจำกัดที่ต้องรู้

- Module 03 มี SQLite knowledge database รุ่นเริ่มต้น 13 รายการ seed จาก `03_pc_build_ai_agent/data/components.json`; URL ผู้ผลิตเป็นแหล่งอ้างอิงที่ต้อง audit/อัปเดตเอง ไม่ได้ sync สด และยังไม่ครอบคลุมตลาดทั้งหมด
- Module 04 ค้นราคา ณ เวลาที่ขอจาก Google Shopping ผ่าน SerpApi แล้วคืน median และช่วงต่ำ–สูงจากผลที่ตรง search terms, เป็น THB เท่านั้น ต้องมี `SERPAPI_API_KEY`
- ช่วงราคาดังกล่าวเป็นข้อมูลอ้างอิงจากผลค้นหา ไม่ใช่ใบเสนอราคาหรือราคาที่รับประกัน; หากจับคู่รุ่นไม่ได้/ราคาหาย ระบบจะแสดง unknown และไม่ยืนยันว่าอยู่ในงบ
- Module 06 ตรวจ socket, support list, memory generation, PSU, connectors และ case clearance จาก facts ที่มี source; BIOS version และ RAM QVL ยังไม่ verified ในฐานข้อมูลเริ่มต้น จึงอาจแสดง needs-review
- ไม่มี provider สำหรับ benchmark หรือ LLM จริง; ไม่สร้างตัวเลข benchmark/คำตอบ LLM ขึ้นมาแทนข้อมูล

## เริ่มใช้งาน

ต้องใช้ SerpApi key เพื่อให้ระบบแสดงช่วงราคาจากการค้นจริง ถ้ายังไม่มี key เว็บและ services เปิดได้ แต่ราคาจะเป็น unknown และผลจะ degraded:

1. สร้าง SerpApi API key
2. ที่ repository root รัน `Copy-Item .env.example .env` แล้วใส่ key ใน `.env`
3. เปิด Docker Desktop แล้วรัน:

```powershell
docker compose up --build -d
docker compose ps
```

เปิด `http://localhost:3000`. คำแนะนำ local development และตรวจ service อยู่ใน [README_RUN.md](README_RUN.md).

## Flow

```text
01 Web -> 02 API -> 03 Sourced component knowledge / selection
                  -> 04 SerpApi reference-price range
                  -> 05 per-request evidence snapshot
                  -> 06 sourced compatibility checks
                  -> 07 budget/compatibility decision
                  -> 08 response with sources and limitations
```

## สถานะรายโมดูล

| Module | หน้าที่ |
|---|---|
| [01 Web App](01_web_app/README.md) | ฟอร์มงบ/การใช้งาน/brand-model และแสดงช่วงราคา/ข้อจำกัด |
| [02 API Backend](02_api_backend/README.md) | Auth สำหรับ development และ orchestration |
| [03 PC Build AI Agent](03_pc_build_ai_agent/README.md) | เลือกชุดสเปกจาก knowledge base ที่มีแหล่ง |
| [04 External Data](04_external_data_services/README.md) | ราคาอ้างอิงผ่าน SerpApi เท่านั้น |
| [05 Data Integration](05_data_integration/README.md) | รวม spec/prices พร้อม provenance ต่อคำขอ |
| [06 Compatibility/Knowledge](06_compatibility_knowledge_services/README.md) | ตรวจ compatibility และ fail closed เมื่อหลักฐานไม่พอ |
| [07 Decision/LLM](07_decision_llm_engine/README.md) | ตัดสินใจด้วย rules; LLM ยังเป็น placeholder |
| [08 Recommendation/Feedback](08_recommendation_feedback/README.md) | format ผล ไม่มีการซื้อขาย |

## ก่อนให้ลูกค้าใช้งานจริง

ต้องมี API key/สิทธิ์ใช้ SerpApi output ที่เหมาะสม, ตรวจและ version ข้อมูลผู้ผลิต/QVL/BIOS, ขยายรุ่นที่รองรับ, เพิ่ม tests จาก live response อย่างจำกัด และทดสอบ end-to-end. ก่อนเปิด public ให้แทน development auth, เปลี่ยน in-memory state เป็น persistent service, ตั้ง monitoring/rate/cost controls และ privacy/retention. การรัน localhost เป็นเพียงการสาธิต/พัฒนา ไม่ใช่ production readiness.
