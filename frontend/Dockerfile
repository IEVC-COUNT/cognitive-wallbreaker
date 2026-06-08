# 认知破壁机 V5.1 — 前端 Docker (生产模式)
# Next.js 14 + React 18
FROM node:20-alpine

WORKDIR /app

# ── 依赖（利用 Docker 缓存层）──
COPY package.json package-lock.json ./
RUN npm ci

# ── 源码 + 构建 ──
COPY . .
RUN npm run build

EXPOSE 3000

# 生产模式启动
CMD ["npm", "start"]
