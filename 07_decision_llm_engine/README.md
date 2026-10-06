# Module 07: Decision and LLM Engine

## หน้าที่และสถานะ

`POST /v1/decision/evaluate` รับ snapshot, compatibility, alternatives และ data quality เพื่อเลือก action ด้วย deterministic policy: compatibility conflict เป็น safety override, จากนั้นพิจารณางบประมาณ, stock/price unknown และทางเลือก. Action ถูก lock ก่อนสร้างข้อความอธิบาย; `GET /health` แสดง policy version.

LLM ไม่ได้ถูกเรียกจริงในปัจจุบัน: `call_llm()` คืน `None` แม้ตั้ง `LLM_API_KEY`; คำอธิบายใช้ fixed template และ `fallback_used=true`. การตั้ง key ไม่ได้เปิดการเชื่อมต่อ LLM. นอกจากนี้ rules คำนวณ total จากราคาที่รู้ แต่ไม่รวมราคาที่ unknown; ห้ามอนุมานว่าเป็น total ครบถ้วนหาก data-quality ระบุ coverage ไม่ครบ.

## แนวทางเมื่อต่อ LLM จริง

- ให้ LLM สรุปเฉพาะ action/evidence ที่ผ่าน deterministic rules; ไม่ให้สร้าง product, price, compatibility fact, citation หรือเปลี่ยน action
- ส่ง source citations พร้อมข้อมูลที่จำเป็นน้อยที่สุด; validate structured output/schema, จำกัด input/output, timeout, retry/cost และป้องกัน prompt injection
- เก็บ `llm_used`, model/version และ fallback status อย่างโปร่งใส; หาก provider error ใช้ fixed template พร้อมแจ้งสถานะ
- เกณฑ์อนุมัติซื้อ/ห้ามซื้อยังเป็น deterministic rules และต้อง fail-closed เมื่อ critical evidence หาย

## ตั้งค่าและรัน

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8500 --reload
python -m pytest -q
```

`LLM_API_KEY` ใน env ปัจจุบันไม่มีผลให้เกิด provider call. ดูลำดับต่อ provider และ requirements ด้าน evidence ที่ [root README](../README.md).
