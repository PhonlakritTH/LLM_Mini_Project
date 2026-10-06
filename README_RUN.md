# Run the PC Spec Builder

ระบบ local นี้เป็นเครื่องมือวางแผนสเปก ไม่ใช่ระบบซื้อขาย. Module 03 โหลด curated compatibility facts 13 รุ่น/ชิ้นส่วนจาก `03_pc_build_ai_agent/data/components.json` และพยายามอ่าน metadata/structured facts สดจาก official manufacturer pages. ราคาอ้างอิงมาจาก Google Shopping ผ่าน SerpApi; คำอธิบายจะมาจาก LLM provider แบบ OpenAI-compatible. หาก credentials/provider ไม่พร้อม ระบบไม่สร้างราคา/คำอธิบายจำลอง.

## Requirements

- Node.js 20.9+ และ npm
- Docker Desktop/Engine (แนะนำสำหรับรันครบทุก service)
- SerpApi API key สำหรับช่วงราคา live และ LLM API key สำหรับคำอธิบายสด

อย่า commit `.env` หรือวาง key ใน frontend/`NEXT_PUBLIC_*`. ตรวจ Terms/สิทธิ์ใช้ข้อมูลจาก SerpApi ก่อนเปิดบริการแก่ลูกค้า.

## Docker Compose (แนะนำ)

จาก repository root:

```powershell
Copy-Item .env.example .env
notepad .env
```

ใส่ API key ในไฟล์ root `.env`:

```text
SERPAPI_API_KEY=ใส่คีย์ SerpApi
LLM_API_KEY=ใส่คีย์ผู้ให้บริการ LLM
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_EXPLAINER=gpt-4o-mini
```

จากนั้นเปิด Docker Desktop แล้วรัน:

```powershell
docker compose up --build -d
docker compose ps
```

เปิด `http://localhost:3000`; API docs อยู่ที่ `http://localhost:8000/docs`. ดู log หากบริการยังไม่พร้อม:

```powershell
docker compose logs --tail 100
```

หยุดด้วย `docker compose down`. State ของ feedback/rate-limit ยังไม่ persist.

## Local services (PowerShell)

เริ่ม service แต่ละตัวใน terminal แยกกัน และติดตั้ง requirements ใน Python environment ของคุณ. เริ่ม Module 04 ก่อน; สร้าง `04_external_data_services/.env` จาก `.env.example` และใส่ `SERPAPI_API_KEY`:

```powershell
Set-Location 04_external_data_services
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8200 --reload
```

จากนั้นเปิด terminal แยกสำหรับ Modules 05–08:

```powershell
Set-Location 05_data_integration
python -m uvicorn app.main:app --port 8300 --reload
```

```powershell
Set-Location 06_compatibility_knowledge_services
python -m uvicorn app.main:app --port 8400 --reload
```

สร้าง `07_decision_llm_engine/.env` จาก `.env.example` แล้วตั้ง `LLM_API_KEY`, `LLM_BASE_URL` และ `LLM_MODEL_EXPLAINER` ให้ตรงผู้ให้บริการ OpenAI-compatible ก่อนส่งคำขอจัดสเปก:

```powershell
Set-Location 07_decision_llm_engine
Copy-Item .env.example .env
# Set LLM_API_KEY, LLM_BASE_URL and LLM_MODEL_EXPLAINER in .env
python -m uvicorn app.main:app --port 8500 --reload
```

```powershell
Set-Location 08_recommendation_feedback
python -m uvicorn app.main:app --port 8600 --reload
```

ใน terminal แยก เปิด Modules 03 และ 02. ใช้ URL และ `INTERNAL_TOKEN` เดียวกันกับ services:

```powershell
Set-Location 03_pc_build_ai_agent
Copy-Item .env.example .env
# Set PRICE_SERVICE_URL=http://localhost:8200
python -m uvicorn app.main:app --port 8100 --reload
```

```powershell
Set-Location 02_api_backend
Copy-Item .env.example .env
# Set AGENT_SERVICE_URL=http://localhost:8100 and URLs for Modules 05-08
python -m uvicorn app.main:app --port 8000 --reload
```

เริ่มเว็บเป็นลำดับสุดท้าย:

```powershell
Set-Location 01_web_app
npm ci
npm run dev
```

## Health checks / tests

| Module | Port | Health |
|---|---:|---|
| 01 Web App | 3000 | `http://localhost:3000` |
| 02 API Backend | 8000 | `/health`, `/ready`, `/docs` |
| 03 PC Build AI Agent | 8100 | `/health` |
| 04 External Data | 8200 | `/health` |
| 05 Data Integration | 8300 | `/health` |
| 06 Compatibility/Knowledge | 8400 | `/health` |
| 07 Decision/LLM | 8500 | `/health` |
| 08 Recommendation/Feedback | 8600 | `/health` |

รัน `python -m pytest -q` ในแต่ละ module ที่ต้องการทดสอบ; เว็บใช้ `npm run build`. Tests ใช้ fixtures/mock เฉพาะใน test code และไม่ได้พิสูจน์ว่า key/provider live ใช้งานได้. ตรวจ response ว่ามี source, เวลาอ้างอิง, price range และ compatibility limitations; `null` หมายถึงไม่มีหลักฐาน ไม่ใช่ศูนย์.
