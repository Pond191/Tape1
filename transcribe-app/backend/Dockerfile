FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# ของจำเป็นสำหรับ build C-extension + เล่นไฟล์เสียง + healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ make python3-dev \
    ffmpeg \
    curl \
    gosu \
 && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app --uid 1000 app

# pip ใหม่ช่วยเรื่อง build พวก wheel
RUN python -m pip install --upgrade pip

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY . .

# Copy entrypoint and normalize line endings for Windows checkouts
COPY deploy/api/start-api.sh /usr/local/bin/start-api
RUN (command -v dos2unix >/dev/null 2>&1 || \
     (apk add --no-cache dos2unix || (apt-get update && apt-get install -y dos2unix))) \
 && dos2unix /usr/local/bin/start-api \
 && chmod +x /usr/local/bin/start-api

# Use this entrypoint
ENTRYPOINT ["/usr/local/bin/start-api"]
