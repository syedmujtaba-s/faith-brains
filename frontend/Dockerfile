# FaithBrains frontend — Next.js standalone production image
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# The /api/v1 rewrite destination is baked into the standalone build —
# it must be the in-network API address, not a runtime env default.
ARG BACKEND_URL=http://api:8000
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
# BACKEND_URL is read at server start for the /api/v1 rewrite proxy
CMD ["node", "server.js"]
