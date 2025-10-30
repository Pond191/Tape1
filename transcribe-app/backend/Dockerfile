FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ make python3-dev \
    ffmpeg \
    curl \
    dos2unix \
    gosu \
 && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app --uid 1000 app

RUN python -m pip install --upgrade pip
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY deploy/api/start-api.sh /usr/local/bin/start-api
RUN dos2unix /usr/local/bin/start-api && chmod +x /usr/local/bin/start-api

ENTRYPOINT ["/usr/local/bin/start-api"]
