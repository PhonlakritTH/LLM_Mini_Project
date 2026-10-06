# AI PC Spec Builder

เว็บช่วยวางแผนและตรวจสอบสเปกคอมพิวเตอร์ แบ่งระบบเป็น 8 โมดูลแยกหน้าที่ เพื่อให้แหล่งข้อมูลสินค้า กฎความเข้ากันได้ และหน้าเว็บพัฒนา/ทดสอบแยกจากกันได้

> **สถานะข้อมูลจริง (อัปเดต 2026-10-06):** ระบบยังไม่ใช่เครื่องมือแนะนำสินค้าที่ตรวจสอบข้อมูลจริงครบวงจร ปัจจุบัน Module 04 ค้นหาราคาได้จาก Google Shopping ผ่าน SerpApi เมื่อกำหนด API key; เป็นราคาที่ค้นพบจากผล Shopping ไม่ใช่ feed ที่ยืนยันจากร้านค้าโดยตรง ส่วน Module 03 สร้างชุดชิ้นส่วนจากรายการตัวอย่างแบบคงที่ ขณะที่ stock, benchmark และสเปกผู้ผลิตยังไม่มี live provider; RAG/ทางเลือกสินค้าและการเรียก LLM ก็ยังไม่พร้อมใช้งาน ระบบจะทำเครื่องหมายข้อมูลขาด/ผล degraded แทนการเติมราคาหรือ stock เอง แต่การมีราคา SerpApi ไม่ได้ทำให้ candidate list กลายเป็น catalog ที่ยืนยันแล้ว

## เริ่มตรงไหน

1. **กำหนดแหล่งข้อมูลที่ได้รับอนุญาตก่อน**: catalog สินค้า/รหัสรุ่นและสเปกจากผู้ผลิตหรือผู้จัดจำหน่าย, ราคาและสถานะจาก retailer feed/API ที่ใช้ได้ตามเงื่อนไข, และแหล่ง benchmark ที่มีวิธีวัดกับใบอนุญาตชัดเจน ระบุภูมิภาค TH, สกุล THB, ความถี่อัปเดต และสิทธิ์จัดเก็บ/แสดงผล
2. **ทำ catalog สินค้าจริงก่อนระบบแนะนำ**: แต่ละรายการต้องมี canonical product ID, ชื่อรุ่นที่แน่นอน, manufacturer part number, หมวดหมู่, สเปกที่จำเป็นต่อ compatibility, แหล่งที่มา, เวลาที่ตรวจสอบ และสถานะเลิกผลิต/แทนรุ่น ห้ามใช้ชื่อกว้างๆ เช่น “16GB DDR5” เป็นสินค้าที่ซื้อได้
3. **เชื่อม provider จริงใน Module 04**: เริ่มจากราคา SerpApi ที่มีอยู่ แต่แสดงให้ชัดว่าเป็นผลค้นหาและให้ผู้ใช้ยืนยันร้าน/ราคา ณ checkout จากนั้นเพิ่ม provider ที่ได้รับอนุญาตสำหรับ stock, specs และ benchmark; เมื่อ provider ไม่พร้อมให้คงค่า unknown
4. **นำ candidate selection ไปใช้ catalog**: Module 03 ต้องค้น/กรองจาก catalog และสเปกตาม budget/use case; เก็บ candidate ID ให้ตรงกันตั้งแต่ราคาไปถึง compatibility อย่าให้ LLM แต่งรุ่นหรือราคา
5. **ทำข้อมูลกลางและกฎตรวจสอบ**: Module 05 รวมข้อมูลพร้อม provenance/freshness; Module 06 ตรวจ socket, CPU/board support, RAM generation, case clearance, PSU headroom/connectors และ BIOS จากข้อมูลอ้างอิงที่มี version
6. **ตัดสินใจแบบ fail-closed**: Module 07 ใช้กฎ deterministic เป็นผู้ตัดสิน; LLM ถ้ามีให้ช่วยเรียบเรียงคำอธิบายจาก evidence ที่ตรวจสอบแล้วเท่านั้น ห้ามเปลี่ยน action หรือเติมตัวเลข
7. **ส่งผลพร้อมข้อจำกัดถึงผู้ใช้**: Module 08 format source, timestamp, confidence, missing/stale fields; Module 01 ให้เลือก/ทบทวนสินค้าและแสดงราคาที่ตรวจพบ ไม่แสดง unavailable ว่าเป็นราคา 0 หรือ stock มี
8. **ผ่านเกณฑ์ก่อนเปิดให้ใช้งานจริง**: ทดสอบ provider ด้วยข้อมูลจริงอย่างจำกัด, ตรวจ product-match, freshness, currency, source URL และ failure path; เพิ่ม monitoring, rate-limit/cost controls, storage และ production auth ก่อน public launch

รายละเอียดสิ่งที่ทำจริงและงานที่ยังขาดในแต่ละโมดูล: [01 Web App](01_web_app/README.md), [02 API Backend](02_api_backend/README.md), [03 PC Build AI Agent](03_pc_build_ai_agent/README.md), [04 External Data](04_external_data_services/README.md), [05 Data Integration](05_data_integration/README.md), [06 Compatibility/Knowledge](06_compatibility_knowledge_services/README.md), [07 Decision/LLM](07_decision_llm_engine/README.md), [08 Recommendation/Feedback](08_recommendation_feedback/README.md).

## ภาพรวมการไหลของข้อมูล

```text
ผู้ใช้
  -> 01 Web App
  -> 02 API Backend (auth, rate limit, orchestration)
  -> 03 PC Build Agent (เลือก candidate จาก catalog — ปัจจุบันยังเป็นรายการคงที่)
  -> 04 External Data (ราคา SerpApi; stock/spec/benchmark ยังไม่มี provider)
  -> 02 API Backend
       -> 05 Data Integration (validate, merge, provenance, freshness)
       -> 06 Compatibility/Knowledge (กฎ compatibility; RAG/alternatives ปิดไว้)
       -> 07 Decision/LLM (กฎตัดสินใจ; LLM ยังเป็น placeholder)
       -> 08 Recommendation/Feedback (จัด response; feedback ยังไม่ต่อกับหน้าเว็บ)
  -> 01 Web App แสดงผลพร้อมแหล่งข้อมูลและข้อจำกัด
```

เมื่อราคา/stock/spec หายหรือบริการปลายทางล้มเหลว ค่าไม่ทราบต้องคงเป็น `null` และผลต้องแสดง degraded/ข้อจำกัด ห้ามสร้างราคาเฉลี่ยหรือแสดงข้อมูลตัวอย่างเป็นข้อมูลจริง ข้อมูลทดสอบใน unit tests ต้องแยกจาก runtime/provider response อย่างชัดเจน

## โมดูลและหน้าที่

| โมดูล | หน้าที่ / สถานะปัจจุบัน |
|---|---|
| [01 Web App](01_web_app/README.md) | Next.js form/results และแสดงผลบางส่วน; ยังไม่มี product picker ที่ดึง catalog |
| [02 API Backend](02_api_backend/README.md) | FastAPI auth สำหรับ dev, rate limit ใน memory และ orchestration; token/idempotency ยังไม่ production |
| [03 PC Build AI Agent](03_pc_build_ai_agent/README.md) | กราฟ deterministic; candidate ปัจจุบัน hard-coded; เรียกข้อมูลผ่าน Module 04 |
| [04 External Data](04_external_data_services/README.md) | ราคา Google Shopping ผ่าน SerpApi; provider อื่นยัง unavailable |
| [05 Data Integration](05_data_integration/README.md) | สร้าง snapshot ต่อ request, lineage/quality; ยังไม่ persist |
| [06 Compatibility/Knowledge](06_compatibility_knowledge_services/README.md) | กฎ deterministic บางส่วน; sample knowledge ปิด, RAG/alternatives ไม่มี provider |
| [07 Decision/LLM](07_decision_llm_engine/README.md) | กฎ deterministic; การเรียก LLM ยัง placeholder |
| [08 Recommendation/Feedback](08_recommendation_feedback/README.md) | จัด response; feedback/queue อยู่ใน memory และหน้าเว็บยังไม่เชื่อม |

## วิธีรันและตรวจสอบ

อ่าน [README_RUN.md](README_RUN.md) สำหรับ Docker Compose และ local services, ports, environment variables และ smoke check. สำหรับ Module 01–02 ดู [README_01_02.md](README_01_02.md).

ทดสอบ Python แยกในแต่ละโมดูล:

```powershell
Set-Location 02_api_backend
python -m pip install -r requirements.txt
python -m pytest -q
```

ทำซ้ำกับ Modules 03–08. ทดสอบเว็บ:

```powershell
Set-Location 01_web_app
npm ci
npm run build
```

การรันเว็บได้สำเร็จไม่ได้หมายความว่า provider ข้อมูลจริงพร้อมใช้งาน; ให้ตรวจ health ของแต่ละ service และผล degraded/source/timestamp ก่อนยอมรับผลแนะนำ

## สิ่งที่ต้องตัดสินใจก่อนเติม live data

- เลือก retailer/product data sources ที่อนุญาตให้ค้น/จัดเก็บ/แสดง; ต้องมี API/feed หรือข้อตกลงที่เหมาะสม หลีกเลี่ยงการ scrape ที่ละเมิด terms
- ระบุแหล่ง official specifications และ benchmark ที่ยอมรับได้ รวมถึงวิธีเก็บ version และอ้างอิง
- กำหนดความใหม่สูงสุดของราคา/stock, region, THB, matching threshold, การจัดการสินค้าหมด/เลิกผลิต และนโยบายเมื่อข้อมูลแหล่งต่างๆ ขัดแย้ง
- เลือกว่าจะเก็บ catalog/snapshot/feedback ที่ใด ระยะเวลาเท่าไร และสิทธิ์เข้าถึงอย่างไร

หากยังไม่กำหนดแหล่งเหล่านี้ ขั้นที่ปลอดภัยคือทำ catalog/schema และ provider interface ให้พร้อม โดยปิดความสามารถที่ไม่มีข้อมูลยืนยันไว้ ไม่ควรสร้าง mock fallback ใน production.
