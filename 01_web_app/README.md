# Module 01: Web App

## หน้าที่และสถานะ

Next.js App Router หน้าเว็บภาษาไทยสำหรับรับความต้องการและแสดงผลตอบกลับจาก Module 02. ปัจจุบันมี Hero, theme light/dark, form งบประมาณ/use case/brand/ชิ้นส่วนเดิม และ panel ผลลัพธ์; ยังไม่มี manual product picker หรือหน้าค้น catalog. UI แสดงราคา/stock ที่ไม่ทราบเป็น unknown และคำเตือนจากผล degraded.

เส้นทางข้อมูล: `form -> lib/schema.ts validation/normalization -> lib/api.ts -> Module 02 /v1/builder/recommendations -> render response`. API client ใช้ development token endpoint; ยังไม่ใช่ระบบ login จริง.

## ข้อมูลจริงที่ UI ต้องรองรับ

- ไม่ฝังราคา/stock/sample product list ใน frontend; ให้ backend ส่ง product ID, ชื่อรุ่นที่ยืนยัน, แหล่งข้อมูล, URL, observed/fetched time และสถานะ freshness
- แสดงราคาและสกุลเงินตามข้อมูลที่ provider ระบุ พร้อมแจ้งว่าราคาเปลี่ยนได้และตรวจซ้ำกับร้านก่อนชำระ
- แสดง unavailable/null แยกจาก `0` และ `มีสินค้า`; แสดง provider/compatibility ข้อจำกัดและข้อมูลขัดแย้งอย่างตรงไปตรงมา
- งานต่อไป: product picker ที่อ่าน catalog API, แสดงแหล่ง/เวลาอัปเดต, เปรียบเทียบ offers และ browser tests สำหรับฟอร์ม/partial/error states

## ตั้งค่าและรัน

```powershell
npm ci
npm run dev
```

เปิด `http://localhost:3000`. ค่า API เริ่มต้นคือ `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`; เปลี่ยนใน `.env.local` หาก API อยู่ที่อื่น ห้ามใส่ secret ในตัวแปร `NEXT_PUBLIC_*`.

```powershell
npm run build
```

ไม่มี browser UI test suite ในตอนนี้. วิธีรันทั้งระบบอยู่ที่ root [README_RUN.md](../README_RUN.md); ภาพรวมและสถานะ data providers อยู่ที่ root [README.md](../README.md).
