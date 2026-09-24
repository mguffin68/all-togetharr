# Node 20 LTS, Alpine. Multi-stage build: install deps + generate Prisma client,
# then a slim runtime image with only the production Next.js standalone output.

FROM node:20-alpine AS base
RUN apk add --no-cache openssl
WORKDIR /app

# --- deps: install all packages (incl. dev) + generate Prisma client ---
FROM base AS deps
COPY package.json package-lock.json ./
COPY prisma ./prisma
RUN npm ci

# --- build: build the Next.js app ---
FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- runtime: minimal image with standalone server + prisma engine + sqlite data ---
FROM base AS runner
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# SQLite data dir, mounted as a volume in docker-compose
ENV DATABASE_URL="file:/data/sqlite.db"
RUN mkdir -p /data
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/prisma ./prisma
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/node_modules/.prisma ./node_modules/.prisma
COPY --from=build /app/node_modules/@prisma/engines ./node_modules/@prisma/engines

EXPOSE 3000
CMD ["node", "server.js"]
