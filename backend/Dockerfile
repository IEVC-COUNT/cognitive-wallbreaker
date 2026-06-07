# 认知破壁机 V5.0 — 后端 Docker
# Python 3.12（OCR 功能需 Node.js，Docker 中暂不包含以加速构建）
FROM python:3.12-slim

WORKDIR /app

# ── Python 依赖（国内阿里云镜像加速）──
COPY requirements_v2.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements_v2.txt

# ── 源码 ──
COPY . .

# ── 数据目录（volume 挂载点）──
RUN mkdir -p /app/../data/memory /app/../data/history

EXPOSE 8920

# 启动
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8920"]
