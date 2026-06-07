# 认知破壁机 V5.0 — 后端 Docker
# Python 3.12 + Node.js (OCR 辅助)
FROM python:3.12-slim

# 安装 Node.js（ocr_helper.js 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python 依赖 ──
COPY requirements_v2.txt .
RUN pip install --no-cache-dir -r requirements_v2.txt

# ── 源码 ──
COPY . .

# ── 数据目录（volume 挂载点）──
RUN mkdir -p /app/../data/memory /app/../data/history

EXPOSE 8920

# 启动
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8920"]
