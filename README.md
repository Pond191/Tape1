# Dialect Transcribe

ระบบถอดเทปภาษาถิ่นไทย + โค้ดสวิตช์ ที่ออกแบบให้พร้อมใช้งานทั้งโหมดเดสก์ท็อปและ Docker โดยมี FastAPI เป็น backend, React (Vite) เป็น frontend และ Celery + Redis สำหรับประมวลผลแบ็กกราวด์

## คุณสมบัติหลัก

- รองรับไฟล์เสียง `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`
- ASR abstraction ครอบ Faster-Whisper/CTranslate2 (production) พร้อม fallback Whisper/PyTorch และ dummy engine สำหรับ unit test
- Speaker diarization (pyannote หรือ energy-based fallback) + word/segment timestamp + confidence
- Post-processing ครบ: punctuation restoration, ITN, normalization, dialect mapping (เหนือ/อีสาน/ใต้ → ไทยกลาง) และ redaction regex
- Language auto-detect + context prompt + custom lexicon
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

### 1. เตรียมสภาพแวดล้อม

ต้องการ Python 3.10+, Node.js 18+, และ ffmpeg (สำหรับแปลงไฟล์เสียง)

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
python -m venv .venv
source .venv/bin/activate
pip install -r transcribe-app/backend/requirements.txt
```

### 2. ดาวน์โหลดโมเดลที่จำเป็น

```bash
bash transcribe-app/scripts/download_models.sh
```

สคริปต์จะสร้างโฟลเดอร์ `models/` และดึงโมเดล Faster-Whisper (ctranslate2), pyannote, fastText
และโมเดลสำรองที่ใช้ใน fallback ทั้งหมด หากพื้นที่จำกัดสามารถแก้สคริปต์ให้ดาวน์โหลดเฉพาะโมเดลที่ต้องการได้

### 3. เปิดบริการ Backend

```bash
uvicorn backend.app:app --reload --app-dir transcribe-app
```

เซิร์ฟเวอร์ API จะเปิดที่ `http://localhost:8000`

### 4. เปิดบริการ Frontend

```bash
cd transcribe-app/frontend
npm install
npm run dev
```

UI dev server จะอยู่ที่ `http://localhost:5173` และจะ proxy คำร้องไปยัง backend ให้อัตโนมัติในโหมดพัฒนา

### 5. ลำดับการใช้งานผ่านเว็บ

1. เปิดเบราว์เซอร์ไปที่ `http://localhost:5173`
2. ปุ่ม “อัปโหลดไฟล์เสียง” จะเปิด dialog ให้เลือกไฟล์ (รองรับ `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`)
3. กำหนดตัวเลือกเสริม เช่น ขนาดโมเดล, เปิด/ปิด diarization, ITN, dialect map, กรอก context prompt หรือ custom lexicon
4. กด “เริ่มถอดเสียง” ระบบจะสร้าง job และ redirect ไปยังหน้ารายการงานอัตโนมัติ
5. หน้า Job List แสดงสถานะ (queued, processing, finished, failed) พร้อมเวลาเริ่ม/สิ้นสุดและเปอร์เซ็นต์ความคืบหน้า
6. เมื่อสถานะเป็น finished สามารถกดเปิด Transcript Viewer เพื่อดูผลแบบ segment-by-segment (มีเวลา, ผู้พูด, confidence)
7. ปุ่มดาวน์โหลดด้านบน Transcript Viewer เลือกส่งออก `.txt`, `.srt`, `.vtt`, หรือ `.jsonl`

### 6. การใช้งานผ่าน REST API

เมื่อ backend เปิดแล้วสามารถเรียก API ได้ตรง ๆ

**สร้างงานถอดเสียง**

```bash
curl -F "file=@/path/to/audio.wav"      -F 'options={"model_size":"large-v3","enable_diarization":true,"enable_punct":true,"enable_itn":true,"enable_dialect_map":true,"custom_lexicon":["Node-RED","MQTT","สงขลานครินทร์"],"context_prompt":"ประชุมทีมไอที"}'      http://localhost:8000/api/transcribe
```

ผลลัพธ์จะได้ `{"job_id": "..."}` ให้เก็บไว้ใช้อ้างอิง

**ตรวจสอบสถานะงาน**

```bash
curl http://localhost:8000/api/jobs/<job_id>
```

จะได้ JSON ที่มี `status`, `progress`, `eta_seconds`, `error` (ถ้ามี)

**ดาวน์โหลดผลลัพธ์**

```bash
curl -L "http://localhost:8000/api/jobs/<job_id>/result?format=srt" -o transcript.srt
```

ในกรณีเปิด dialect mapping ระบบจะให้ endpoint เพิ่มเติม `/result/inline?variant=dialect` สำหรับผลแบบไทยถิ่น และ `/result/inline?variant=standard`
สำหรับเวอร์ชันแปลงเป็นไทยกลาง

**ตัวอย่างการรับผลแบบ JSON เต็ม**

```bash
curl http://localhost:8000/api/jobs/<job_id>/result/inline | jq
```

จะเห็น `segments`, `speakers`, `confidence`, `dialect_variants` พร้อม metadata ครบสำหรับนำไปใช้งานต่อ

### 7. การหยุดบริการ dev

กด `Ctrl+C` ในเทอร์มินัลที่รัน uvicorn และ `npm run dev`
จากนั้นปิด virtualenv ด้วย `deactivate`

## รันด้วย Docker / Compose

### 1. เตรียมสิ่งแวดล้อม

- ติดตั้ง Docker และ Docker Compose plugin
- ตรวจสอบว่า GPU driver (ถ้ามี) ถูกตั้งค่ากับ Docker ตามคู่มือ NVIDIA Container Toolkit

### 2. สร้างและเปิดบริการ

```bash
cd transcribe-app
docker compose -f deploy/docker-compose.yml up -d --build
```

Compose จะสร้าง container สำหรับ `api`, `worker`, `redis`, `db`, `web`, `nginx`

### 3. ตรวจสอบสถานะ

```bash
docker compose -f deploy/docker-compose.yml ps
```

เมื่อทุกบริการเป็น `running` ให้เปิดเบราว์เซอร์ไปที่ `http://localhost:8080`

### 4. ปิดระบบ

```bash
docker compose -f deploy/docker-compose.yml down
```

ถ้าต้องการล้าง volume (เช่น ลบไฟล์งานและฐานข้อมูล) ให้เพิ่ม `-v`

```bash
docker compose -f deploy/docker-compose.yml down -v
```

## สเปค API

### POST `/api/transcribe`
อัปโหลดไฟล์เสียงพร้อม options (JSON string)

ตัวอย่าง curl:

```bash
curl -F "file=@sample.wav" \
     -F 'options={"model_size":"large-v3","enable_diarization":true,"enable_punct":true,"enable_itn":true,"enable_dialect_map":true,"custom_lexicon":["Node-RED","MQTT","สงขลานครินทร์"]}' \
     http://localhost:8000/api/transcribe
```

Response: `{ "job_id": "..." }`

### GET `/api/jobs/{job_id}`
ดูสถานะงานและ progress

### GET `/api/jobs/{job_id}/result?format=txt|srt|vtt|jsonl`
ดาวน์โหลดผลลัพธ์ฟอร์แมตต่าง ๆ

### GET `/api/jobs/{job_id}/result/inline`
รับ JSON พร้อมข้อความถอดเทป, segments, dialect mapping

พารามิเตอร์เสริม:

- `variant=standard` (ค่าเริ่มต้น) – ข้อความไทยกลางหลัง post-process ครบ
- `variant=dialect` – ข้อความตามภาษาถิ่นต้นฉบับก่อน mapping
- `redacted=true` – เปิดการเบลอข้อมูลส่วนบุคคลด้วย regex redaction

### GET `/api/health`
ตรวจสอบการพร้อมใช้งาน (รวม GPU availability)

## การทดสอบ

```bash
pytest transcribe-app/backend/tests
```

สคริปต์ benchmark:

```bash
python transcribe-app/scripts/benchmark.py transcribe-app/backend/tests/data/sample.wav
```

## คำแนะนำเรื่องความแม่นยำ

- คุณภาพเสียง, ไมค์, เสียงรบกวน และการพูดซ้อน ส่งผลต่อความแม่นยำ
- ใช้ custom lexicon + context prompt เพื่อช่วยลด WER โดยเฉพาะงานเฉพาะด้าน
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
