FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# ของจำเป็นสำหรับ build C-extension + เล่นไฟล์เสียง + healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ make python3-dev \
    ffmpeg \
    curl \
 && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app --uid 1000 app

# pip ใหม่ช่วยเรื่อง build พวก wheel
RUN python -m pip install --upgrade pip

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ให้ Uvicorn รันแน่ๆ (ถ้า Dockerfile เดิมมี CMD อยู่แล้วข้ามได้)
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
