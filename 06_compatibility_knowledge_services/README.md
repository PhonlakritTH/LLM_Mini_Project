# Module 06: Compatibility and Knowledge Services

## หน้าที่

ตรวจ snapshot ของ build จาก facts ที่มีแหล่งอ้างอิง: CPU/motherboard socket และ CPU support list, memory generation, PSU wattage/connectors, GPU length/case clearance และ board/case form factor. ถ้าข้อมูล critical หรือ provenance หาย จะให้ `NEEDS_REVIEW`; ความขัดแย้งชัดเจนจะเป็น `INCOMPATIBLE`. RAG และ alternative retrieval ยังปิด/ไม่มี live source และไม่ใช้ sample data เป็นข้อเท็จจริง.

ฐานความรู้เริ่มต้นใน Module 03 มี BIOS-version และ RAM-QVL validation เป็น `not_verified`; จึงยังไม่ควรอ้างว่า build ผ่าน compatibility ครบ แม้ socket และชนิด RAM จะตรงกัน. เพิ่มรุ่นได้เมื่อมี source, version, units และหลักฐาน support matrix ที่ตรวจสอบได้.

## API และการรัน

`POST /v1/knowledge/assess` ใช้ `X-Internal-Token`; `GET /health` รายงาน model/schema versions.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8400 --reload
python -m pytest -q
```

เพิ่ม compatibility rules พร้อม tests เมื่อเพิ่ม fields/parts ใหม่; อย่าเปลี่ยน unknown ให้ compatible โดย default. วิธีรันทั้งระบบ: [README_RUN.md](../README_RUN.md).
