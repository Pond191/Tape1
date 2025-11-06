# backend/Dockerfile
FROM python:3.11-jammy

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# OS deps (Ubuntu Jammy has execstack)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ make python3-dev \
    libgomp1 \
    ffmpeg \
    curl \
    dos2unix \
    gosu \
    execstack \
 && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN addgroup --system app && adduser --system --ingroup app --uid 1000 app

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install requirements
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Fix executable stack on ctranslate2 shared libs
# (ignore if none found)
RUN bash -lc 'shopt -s nullglob; for so in /usr/local/lib/python*/site-packages/ctranslate2/libctranslate2-*.so; do echo "Clearing execstack on $so"; execstack -c "$so" || true; done'

# Copy application code
COPY . .

# Install start scripts
COPY deploy/api/start-api.sh /usr/local/bin/start-api
COPY deploy/api/start-worker.sh /usr/local/bin/start-worker
RUN dos2unix /usr/local/bin/start-api /usr/local/bin/start-worker \
    && chmod +x /usr/local/bin/start-api /usr/local/bin/start-worker

# Prepare storage dir and set permissions
RUN mkdir -p /data /data/uploads /data/jobs /data/logs && chown -R app:app /data

USER app

ENTRYPOINT ["/usr/local/bin/start-api"]
