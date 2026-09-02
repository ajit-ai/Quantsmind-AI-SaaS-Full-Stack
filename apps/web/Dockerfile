FROM node:20-alpine AS build
WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
RUN npm install -g pnpm && pnpm install --filter @quantsmind/web || npm install
COPY apps/web ./apps/web
RUN pnpm --filter @quantsmind/web build || npm --prefix apps/web run build

FROM nginx:alpine
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
