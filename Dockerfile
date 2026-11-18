FROM node:22-bookworm-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATABASE=/data/buro.sqlite
WORKDIR /srv/buro
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --system --uid 10001 --no-create-home buro && install -d -o buro -g buro -m 700 /data
COPY app/ app/
COPY docs/ docs/
COPY wsgi.py LICENSE ./
COPY --from=ui /ui/dist/ frontend/dist/
USER buro
EXPOSE 8080
CMD ["gunicorn","--bind=0.0.0.0:8080","--workers=1","--threads=4","--no-control-socket","--timeout=40","--umask=0077","wsgi:app"]
