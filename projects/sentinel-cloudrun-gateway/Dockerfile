FROM node:22-alpine AS explorer-build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/index.html web/tsconfig.json web/vite.config.ts ./
COPY web/src ./src
ARG VITE_SENTINEL_API_BASE=
ENV VITE_SENTINEL_API_BASE=${VITE_SENTINEL_API_BASE}
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements-gateway.txt .
RUN pip install --no-cache-dir -r requirements-gateway.txt
COPY sentinel ./sentinel
COPY migrations ./migrations
COPY tools ./tools
COPY --from=explorer-build /web/dist ./web-dist
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "sentinel.api:app", "--host", "0.0.0.0", "--port", "8080"]
