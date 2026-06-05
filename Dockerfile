FROM node:20-bookworm-slim AS frontend

WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install --include=dev --legacy-peer-deps
COPY frontend/ ./
ENV REACT_APP_BACKEND_URL=
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY --from=frontend /app/frontend/build ./frontend/build

ENV PORT=8080
CMD ["sh", "-c", "cd backend && uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}"]
