# 认知破壁机 V5.0 — 前端 Docker
# Next.js 14 + React 18
FROM node:20-alpine

WORKDIR /app

# ── 依赖（利用 Docker 缓存层）──
COPY package.json package-lock.json ./
RUN npm ci

# ── 源码 ──
COPY . .

EXPOSE 3000

# 开发模式启动
CMD ["npm", "run", "dev"]
