# Dialect Transcribe

ระบบถอดเทปภาษาถิ่นไทย + โค้ดสวิตช์ ที่ออกแบบให้พร้อมใช้งานทั้งโหมดเดสก์ท็อปและ Docker โดยมี FastAPI เป็น backend, React (Vite) เป็น frontend และ Celery + Redis สำหรับประมวลผลแบ็กกราวด์

## คุณสมบัติหลัก

- รองรับไฟล์เสียง `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`
- ASR abstraction ครอบ Faster-Whisper/CTranslate2 (production) พร้อม fallback Whisper/PyTorch และ dummy engine สำหรับ unit test
- Speaker diarization (pyannote หรือ energy-based fallback) + word/segment timestamp + confidence
- Post-processing ครบ: punctuation restoration, ITN, normalization, dialect mapping (เหนือ/อีสาน/ใต้ → ไทยกลาง) และ redaction regex
- Language auto-detect พร้อมสวิตช์ Dialect mapping
- Export ผลลัพธ์ `.txt`, `.srt`, `.vtt`, `.jsonl`
- REST API, เว็บ UI (React) สำหรับอัปโหลด/ติดตามสถานะ/ดู transcript และดาวน์โหลดผลลัพธ์
- Queue worker (Celery) และ PostgreSQL เก็บเมทาดาต้า/ผลลัพธ์, Redis เป็น broker
- Scripts สำหรับโหลดโมเดล (download_models.sh) และ benchmark (jiwer)

> **หมายเหตุ:** โค้ดใน repository เน้นโครงสร้าง production-ready พร้อม abstraction/stub สำหรับรันทดสอบในสภาพแวดล้อมเบา หากต้องการความแม่นยำเต็มรูปแบบ ต้องติดตั้งโมเดลจริงตามคำแนะนำด้านล่าง

## โครงสร้างโปรเจ็กต์

```
transcribe-app/
  backend/                 # FastAPI + Celery worker + SQLAlchemy models/tests
  frontend/                # React (Vite) UI
  deploy/                  # docker-compose + nginx proxy
  scripts/                 # download models, benchmark pipeline
```

รายละเอียดไฟล์สำคัญอยู่ใน docstring และคอมเมนต์ของแต่ละโมดูล

## การติดตั้งและใช้งาน (Dev mode)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r transcribe-app/backend/requirements.txt
bash transcribe-app/scripts/download_models.sh  # ดึงโมเดลที่จำเป็น (แก้ path ตามต้องการ)
uvicorn backend.app:app --reload --app-dir transcribe-app
# อีกเทอร์มินัลสำหรับ frontend
cd transcribe-app/frontend
npm install
npm run dev
```

Backend จะเปิดที่ `http://localhost:8000`, Frontend dev server ที่ `http://localhost:5173`

## รันด้วย Docker / Compose

> ต้องการ Docker Engine และ Docker Compose plugin เวอร์ชันล่าสุด

```bash
cd transcribe-app
docker compose -f deploy/docker-compose.yml build
docker compose -f deploy/docker-compose.yml up -d
```

คำสั่งแรกจะ build image ของ backend/frontend/worker ให้พร้อม จากนั้น `up -d` จะเปิดทุก service (Postgres, Redis, API, Worker, Frontend, Nginx)

ตรวจสอบสถานะ:

```bash
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs -f api
```

เมื่อทุกอย่างพร้อม ให้เปิด `http://localhost:8080` (ผ่าน Nginx) หรือ `http://localhost:8000` (ตรงจาก API)

## สเปค API

### POST `/api/upload` และ `/api/transcribe`
อัปโหลดไฟล์เสียง (multipart/form-data) พร้อมเลือกโมเดลและเปิด/ปิด Dialect mapping. ทั้งสอง path ให้ผลลัพธ์เท่ากันเพื่อรองรับ client รุ่นเก่าและใหม่

ตัวอย่าง curl:

```bash
curl -F "file=@sample.wav" \
     -F "model_size=medium" \
     -F "enable_dialect_map=true" \
     http://localhost:8080/api/upload
```

Response: `{ "id": "...", "status": "pending" }`

### GET `/api/jobs/{job_id}`
ดูสถานะ ปัญหา (ถ้ามี) ตัวถอดเทป และลิงก์ดาวน์โหลดผลลัพธ์

### GET `/api/jobs/{job_id}/txt|srt|vtt|jsonl`
ดาวน์โหลดไฟล์ผลลัพธ์แต่ละฟอร์แมตโดยตรง

### GET `/api/health`
ตรวจสอบการพร้อมใช้งาน (รวม GPU availability)

## การทดสอบ

```bash
pytest transcribe-app/backend/tests
```

หรือถ้าใช้ Docker Compose แล้ว services เปิดอยู่ สามารถรันใน container API ได้ด้วย:

```bash
docker compose -f deploy/docker-compose.yml exec api pytest backend/tests
```

สคริปต์ benchmark:

```bash
python transcribe-app/scripts/benchmark.py transcribe-app/backend/tests/data/sample.wav
```

## คำแนะนำเรื่องความแม่นยำ

- คุณภาพเสียง, ไมค์, เสียงรบกวน และการพูดซ้อน ส่งผลต่อความแม่นยำ
- เปิด Dialect mapping เมื่อเหมาะสมเพื่อช่วยให้ข้อความเป็นไทยกลางได้แม่นยำขึ้น
- สำหรับภาษาถิ่นเฉพาะ แนะนำสร้าง dialect mapping CSV เพิ่มเติมเพื่อปรับ post-processing
- ระบบไม่ส่งข้อมูลออกอินเทอร์เน็ต (เหมาะกับการใช้งานออฟไลน์)

## การตั้งค่าความเป็นส่วนตัว

- Logging จำกัดเฉพาะเมทาดาต้า, ไม่มีการเก็บเนื้อหาจริงโดยดีฟอลต์
- เปิด redaction ด้วย `TRANSCRIBE_ENABLE_REDACTION=1` (regex ปิดข้อมูลบัตร/โทรศัพท์/บัญชี)
- ตั้งค่า retention ผ่าน env `TRANSCRIBE_RETENTION_DAYS`

## การปรับใช้ production

1. เตรียมโมเดล Faster-Whisper (CTranslate2) และ pyannote ใน volume ที่ worker/api เข้าถึงได้
2. ตั้งค่า env ให้ตรงกับฮาร์ดแวร์ (เช่น `TRANSCRIBE_ENABLE_GPU=1`)
3. เปิด Celery worker หลาย instance ตามปริมาณงาน และใช้ Redis/DB ที่พร้อมใช้งานจริง
4. เชื่อมต่อระบบ Monitoring (Prometheus/Grafana) ผ่าน log/metrics ที่ Celery + FastAPI รองรับ

## License

MIT
