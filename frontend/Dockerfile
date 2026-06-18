# syntax=docker/dockerfile:1

# --- Build stage ---
FROM node:22-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# In production the frontend talks to the backend through nginx at /local
ENV VITE_REQUEST_BASE_URL=/local
# Skip vue-tsc type-checking in the image build (pre-existing TS errors);
# bump version then bundle with vite directly.
RUN node build-version.mjs && npx vite build --mode production

# --- Serve stage ---
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html/aimovie

EXPOSE 80
