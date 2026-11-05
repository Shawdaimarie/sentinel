FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src
ARG VITE_SENTINEL_API_BASE=http://127.0.0.1:8080
ENV VITE_SENTINEL_API_BASE=${VITE_SENTINEL_API_BASE}
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 8080
