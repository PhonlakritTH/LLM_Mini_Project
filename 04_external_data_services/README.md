# Module 04: External Data Services

## หน้าที่และสถานะ

เป็น boundary สำหรับเรียก data providers ภายนอกและแปลงผลเป็น response ที่ระบบใช้ได้. ปัจจุบัน provider ที่เรียกได้จริงมีเฉพาะ **price search ผ่าน SerpApi Google Shopping**; `StockPrimary`, `BenchmarkPrimary`, `SpecPrimary` ยังเป็น unavailable provider และคืนข้อมูลว่าง/degraded.

ผลราคาที่ได้เป็น listing จาก Google Shopping ไม่ใช่การรับประกันว่าร้านมีของหรือราคายังเป็นปัจจุบันเมื่อ checkout. ระบบ match title ด้วย token ที่ query ระบุและเลือก listing ราคาต่ำสุดจากผลที่เข้าเกณฑ์; ควรเพิ่ม canonical product ID, match score, จำนวน retailer offers และ review ที่มองเห็นได้ก่อนใช้ตัดสินใจซื้อ.

## Endpoint และการตั้งค่า

`POST /v1/external/query` ต้องมี `X-Internal-Token`, รับ `part_ids`, `fields` (`price`, `stock`, `benchmark`, `spec`) และ locale. Response รวมรายการข้อมูล, provider health, coverage และ degraded flag. `GET /health` ตรวจ process เท่านั้น ไม่ยืนยัน provider health.

ตั้ง `SERPAPI_API_KEY` และ configuration ของ locale (`google.co.th`, Thailand, THB/Bangkok) ใน environment. ห้าม commit key. สำหรับ Docker ใช้ root `.env`; สำหรับ local run ใส่ใน `04_external_data_services/.env`.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8200 --reload
python -m pytest -q
```

Unit tests ใช้ mocked HTTP responses; การผ่าน tests ไม่ได้ยืนยันว่า key/provider live ใช้ได้จริง.

## ลำดับเพิ่มแหล่งข้อมูลจริง

1. ทำ inventory provider, API/feed access, license/terms, region, rate/cost limit และ SLA ก่อน implementation
2. เพิ่ม provider แยกตาม data type: retailer price/stock, manufacturer specs, benchmark source พร้อม attribution/source URL และ observed/fetched/expiry timestamps
3. normalize ราคาเป็น THB โดยไม่แปลง currency แบบสมมติ; เก็บ raw source/offer identity สำหรับ audit
4. คืน missing/mismatched/stale/conflicting เป็น unknown พร้อม health/degraded reason; cache TTL ต้องไม่เกิน freshness policy ของแหล่งนั้น
5. ทดสอบทั้ง replay fixtures และ live smoke test ที่รันเฉพาะเมื่อ credentials ถูกกำหนดอย่างชัดเจน

## Adapter slots (ปิดเมื่อยังไม่มี source)

Module มี adapter contract แบบ async `call(part_ids) -> {"data": ..., "latency_ms": ...}`. `StockPrimary`, `BenchmarkPrimary` และ `SpecPrimary` ปัจจุบันเป็น disabled stubs ที่คืน provider-unavailable; ไม่มี retailer URL/API key ปลอมให้ตั้งค่าแล้วเปิดใช้ได้. `PricePrimary` เรียก SerpApi เฉพาะเมื่อมี `SERPAPI_API_KEY`; คีย์นี้เปิด Google Shopping search เท่านั้น ไม่เปิด stock/spec/benchmark และไม่ยืนยัน catalog identity.

เมื่อได้ API/feed ที่ได้รับอนุญาต ให้เพิ่ม adapter เฉพาะ vendor และ mapping/test ต่อ field; อย่าเพิ่ม generic URL ที่คาดเดารูปแบบ payload. Adapter ใหม่จะเปิดใช้ได้เมื่อมี credentials จริง, source attribution, exact product matching, units/currency, freshness policy, timeout/error handling และ tests ยืนยันว่า response ผิด/ว่างไม่กลายเป็นข้อมูลสำเร็จ. จนกว่าจะผ่านเงื่อนไขเหล่านี้ provider ต้องคืน unavailable และระบบต้องแสดง degraded.

ดูภาพรวม real-data gates และ flow ที่ [root README](../README.md); คำสั่งรันทั้งหมดที่ [README_RUN.md](../README_RUN.md).
