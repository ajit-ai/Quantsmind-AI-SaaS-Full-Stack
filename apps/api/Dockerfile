FROM node:20-alpine
WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY apps/api/package.json ./apps/api/
COPY packages ./packages
RUN npm install -g pnpm && pnpm install --filter @quantsmind/api || npm install
COPY apps/api ./apps/api
WORKDIR /app/apps/api
RUN npx prisma generate || echo "prisma generate skipped (no DB)"
RUN npm run build || npx tsc
EXPOSE 3000
CMD ["node", "dist/main.js"]
