# Module 04: External Data Services

## ขอบเขต

ดึงเฉพาะ **ราคาอ้างอิง** จาก Google Shopping ผ่าน SerpApi แล้วสร้าง median และ low–high range จากผลที่สกุลเป็น THB และตรงกับ `search_terms` ของรุ่น. ไม่ให้บริการ stock, benchmark, manufacturer specs, retailer selection, checkout หรือ purchase links.

ผลค้นหาเป็น snapshot ของ search results ไม่ใช่ใบเสนอราคาหรือราคา/ความพร้อมขายที่รับประกัน. `observed_at` คือเวลาที่ระบบดึงผล; ความถี่/จำนวน offer ขึ้นกับ Google Shopping. เมื่อ API key หาย, query ไม่ตรงรุ่น หรือ coverage ไม่ครบ จะส่ง missing/degraded แทนการเติมราคา.

## Endpoint และการตั้งค่า

- `POST /v1/external/query` ต้องมี `X-Internal-Token`; รับ `part_ids`, `search_terms`, locale และคืนราคาอ้างอิงกับ provider health/coverage
- `GET /health` ตรวจ process เท่านั้น ไม่ยืนยัน SerpApi credentials/provider

ตั้ง `SERPAPI_API_KEY` ใน root `.env` เมื่อใช้ Docker หรือ `04_external_data_services/.env` เมื่อรัน local. ใช้ `google.co.th`, `THB` และ timezone `Asia/Bangkok` ตาม configuration. ห้าม commit API key และตรวจ Terms/สิทธิ์การใช้ผลลัพธ์ก่อนเปิดบริการแก่ลูกค้า.

`GET /health` ตอบ `ok` แม้ credentials ใช้ไม่ได้. ให้ตรวจ `provider_health` จาก `POST /v1/external/query`; `status=401` หมายถึง SerpApi ปฏิเสธ key ที่ service ใช้อยู่ (เช่น key ไม่ถูกต้องหรือถูกเพิกถอน) ไม่ได้แปลว่า key เพียงมีค่าอยู่ใน environment แล้วใช้งานได้. เปลี่ยน key ในไฟล์ `.env` ที่ตรงกับวิธีรัน แล้วโหลดค่าใหม่:

```powershell
# Docker (จากโฟลเดอร์รากโปรเจกต์)
docker compose up -d --force-recreate external_data

# รัน local (หยุด process เดิมก่อน แล้วเริ่มใหม่จากโฟลเดอร์ Module 04)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8200
```

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8200 --reload
python -m pytest -q
```

Tests ใช้ mock HTTP เฉพาะใน tests; runtime ไม่มีราคา fallback. ดูการตั้งค่าระบบทั้งหมดที่ [README_RUN.md](../README_RUN.md).
