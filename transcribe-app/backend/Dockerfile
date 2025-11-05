FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/app/.local/bin:${PATH}"

WORKDIR /app

# Runtime libs ที่จำเป็นต่อ faster-whisper และการแปลงเสียง
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    ffmpeg \
    ca-certificates \
    curl \
    dos2unix \
    gosu \
    # build tools เผื่อบาง wheel ต้องคอมไพล์ (จะใหญ่ขึ้นเล็กน้อย แต่นิ่ง)
    build-essential gcc g++ make python3-dev \
 && rm -rf /var/lib/apt/lists/*

# non-root user
RUN addgroup --system app && adduser --system --ingroup app --uid 1000 app

# Python deps
RUN python -m pip install --upgrade pip
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# โค้ดโปรเจกต์
COPY . .

# สคริปต์สตาร์ท
COPY deploy/api/start-api.sh /usr/local/bin/start-api
COPY deploy/api/start-worker.sh /usr/local/bin/start-worker
RUN dos2unix /usr/local/bin/start-api /usr/local/bin/start-worker \
 && chmod +x /usr/local/bin/start-api /usr/local/bin/start-worker

# ค่าเริ่มต้นให้ api; worker จะ override ใน docker-compose
ENTRYPOINT ["/usr/local/bin/start-api"]
