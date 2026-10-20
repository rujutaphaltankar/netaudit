FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
# Empty base URL = same-origin; nginx proxies /api to the backend.
ARG VITE_API_BASE_URL=""
ARG VITE_SHOW_DEMO_HINT="false"
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL VITE_SHOW_DEMO_HINT=$VITE_SHOW_DEMO_HINT
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
