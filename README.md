# AI PC Spec Builder

ระบบช่วยวางแผนสเปกคอมตามงบ การใช้งาน ยี่ห้อ/รุ่นที่สนใจ พร้อมตรวจ compatibility และแสดงราคาอ้างอิงเป็นช่วง ระบบนี้ **ไม่ใช่ร้านค้า**: ไม่มี stock, checkout หรือ order; แสดงลิงก์ค้นหาสินค้า BaNANA/Amazon เพื่อให้ผู้ใช้ตรวจ offer และราคาปัจจุบันบนเว็บร้านเอง.

## ข้อมูลที่ใช้และข้อจำกัดที่ต้องรู้

- Module 03 มี SQLite curated compatibility catalog รุ่นเริ่มต้น 13 รายการ seed จาก `03_pc_build_ai_agent/data/components.json`; ในแต่ละคำขอจะดึง metadata/structured facts สดจากหน้า manufacturer URL ของชิ้นส่วนที่เลือก โดยแสดงสถานะ/เวลาที่ดึง และไม่เขียนทับ facts ที่ curated. URL ที่อ่านไม่ได้หรือไม่มีข้อมูล structured จะถูกระบุว่า degraded.
- Module 04 ค้นราคา ณ เวลาที่ขอจาก Google Shopping ผ่าน SerpApi แล้วคืน median และช่วงต่ำ–สูงจากผลที่ตรง search terms, เป็น THB เท่านั้น ต้องมี `SERPAPI_API_KEY`
- ช่วงราคาดังกล่าวเป็นข้อมูลอ้างอิงจากผลค้นหา ไม่ใช่ใบเสนอราคาหรือราคาที่รับประกัน; หากจับคู่รุ่นไม่ได้/ราคาหาย ระบบจะแสดง unknown และไม่ยืนยันว่าอยู่ในงบ
- Module 06 ตรวจ socket, support list, memory generation, PSU, connectors และ case clearance จาก facts ที่มี source; BIOS version และ RAM QVL ยังไม่ verified ในฐานข้อมูลเริ่มต้น จึงอาจแสดง needs-review
- Module 07 เรียก LLM แบบ OpenAI-compatible จริงเพื่ออธิบาย action ที่ deterministic rules ล็อกไว้; ต้องตั้ง `LLM_API_KEY`. หาก provider ใช้ไม่ได้ ระบบคืน error แทน template/fallback; LLM ห้ามสร้างราคา/benchmark หรือเปลี่ยนการตัดสินใจ
- ไม่มี provider benchmark จริง; benchmark ไม่ถูกสร้างขึ้นแทนข้อมูล
- ลิงก์ร้านค้าเป็น search links ฟรีแบบไม่ใช้ API และไม่อ้างสต็อก/ราคา; SerpApi มี free tier จำกัดจำนวนคำขอต่อเดือน เป็นตัวเลือกแยกสำหรับราคาอ้างอิงจากผล Shopping

## เริ่มใช้งาน

ตั้ง key ทั้งสองรายการเพื่อให้ระบบแสดงช่วงราคาจากการค้นจริงและคำอธิบาย LLM สด:

1. เตรียม SerpApi API key และ API key จากผู้ให้บริการที่รองรับ OpenAI-compatible Chat Completions/JSON mode
2. ที่ repository root รัน `Copy-Item .env.example .env` แล้วใส่ `SERPAPI_API_KEY` และ `LLM_API_KEY` ใน `.env`; ปรับ `LLM_BASE_URL`/`LLM_MODEL_EXPLAINER` ถ้าใช้ผู้ให้บริการรายอื่น
3. เปิด Docker Desktop แล้วรัน:

```powershell
docker compose up --build -d
docker compose ps
```

เปิด `http://localhost:3000`. คำแนะนำ local development และตรวจ service อยู่ใน [README_RUN.md](README_RUN.md).

## Flow

```text
01 Web -> 02 API -> 03 Curated compatibility + live manufacturer-page facts
                  -> 04 SerpApi reference-price range
                  -> 05 per-request evidence snapshot
                  -> 06 sourced compatibility checks
                  -> 07 locked rules decision + live LLM explanation
                  -> 08 response with sources and limitations
```

## สถานะรายโมดูล

| Module | หน้าที่ |
|---|---|
| [01 Web App](01_web_app/README.md) | ฟอร์มงบ/การใช้งาน/brand-model และแสดงช่วงราคา/ข้อจำกัด |
| [02 API Backend](02_api_backend/README.md) | Auth สำหรับ development และ orchestration |
| [03 PC Build AI Agent](03_pc_build_ai_agent/README.md) | เลือกชิ้นส่วนจาก compatibility catalog และดึงหลักฐานหน้า manufacturer สด |
| [04 External Data](04_external_data_services/README.md) | ราคาอ้างอิงผ่าน SerpApi เท่านั้น |
| [05 Data Integration](05_data_integration/README.md) | รวม spec/prices พร้อม provenance ต่อคำขอ |
| [06 Compatibility/Knowledge](06_compatibility_knowledge_services/README.md) | ตรวจ compatibility และ fail closed เมื่อหลักฐานไม่พอ |
| [07 Decision/LLM](07_decision_llm_engine/README.md) | ตัดสินใจด้วย rules ที่ล็อกผล แล้วอธิบายผ่าน live OpenAI-compatible LLM |
| [08 Recommendation/Feedback](08_recommendation_feedback/README.md) | format ผล ไม่มีการซื้อขาย |

## ก่อนให้ลูกค้าใช้งานจริง

ต้องมี API keys/สิทธิ์ใช้ output ที่เหมาะสม, ตรวจและ version compatibility facts/QVL/BIOS, ขยายรุ่นที่รองรับ, เพิ่ม tests จาก live response อย่างจำกัด และทดสอบ end-to-end. หน้า manufacturer อาจบล็อกการอ่านอัตโนมัติ; ระบบจะรายงาน degraded และยังคงใช้ curated facts โดยไม่แอบอ้างว่า refresh แล้ว. ก่อนเปิด public ให้แทน development auth, เปลี่ยน in-memory state เป็น persistent service, ตั้ง monitoring/rate/cost controls และ privacy/retention. การรัน localhost เป็นเพียงการสาธิต/พัฒนา ไม่ใช่ production readiness.
