# --- Stage 1: build the frontend static bundle -----------------------------
FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# Same-origin deployment: the backend serves both the API and these static
# files, so the built client should call the API with relative paths instead
# of baking in a host (see backendClient.ts's BASE_URL fallback).
ENV VITE_API_BASE_URL=""
RUN npm run build

# --- Stage 2: backend image, serving the API + built frontend --------------
FROM python:3.11-slim AS backend

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY --from=frontend-build /app/frontend/dist ./static

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
