FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=http://127.0.0.1:9160
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html ./index.html
COPY vite.config.js ./vite.config.js
COPY src ./src

RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1
