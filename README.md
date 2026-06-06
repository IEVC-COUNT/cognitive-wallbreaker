# 认知破壁机 · Cognitive Wallbreaker v2.0

AI 深度决策推演 — 击碎隐性假设，穿透认知盲区

## 项目结构

```
cognitive-wallbreaker/
├── README.md
├── .env.example
├── backend/
│   ├── main.py              ← FastAPI 后端
│   ├── engine.py            ← 核心推演引擎
│   ├── memory_manager.py    ← Mem0 长期记忆
│   ├── bot.py               ← Telegram Bot
│   └── requirements_v2.txt  ← Python 依赖
├── frontend/
│   ├── app/
│   │   ├── page.tsx         ← 主页面
│   │   ├── layout.tsx       ← 根布局
│   │   └── globals.css      ← 全局样式
│   ├── package.json
│   ├── tailwind.config.ts
│   └── next.config.js
├── start-backend.bat
└── start-frontend.bat
```

## 环境变量配置

复制 `.env.example` 为 `.env` 并填写：

```bash
# 必填 — OpenAl 兼容 API
OPENAI_API_KEY=sk-你的API密钥
OPENAI_BASE_URL=http://127.0.0.1:4000/v1

# 可选 — 模型选择
WALLBREAKER_MODEL=deepseek-v4-flash

# 可选 — Telegram Bot（不需要 Bot 功能可不填）
TELEGRAM_BOT_TOKEN=你的Bot_Token

# 可选 — Mem0（需要 Qdrant）
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## 快速启动

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements_v2.txt
```

### 2. 确保 DeepSeek 代理在运行

```bash
# 代理应在 4000 端口运行
curl http://127.0.0.1:4000/v1/models
```

### 3. 启动后端 API (端口 8900)

```bash
cd backend
python main.py
# → http://localhost:8900
# → API 文档: http://localhost:8900/docs
```

### 4. 启动前端 (端口 3000)

```bash
cd frontend
npm install    # 首次运行
npm run dev
# → http://localhost:3000
```

### 5. (可选) 启动 Telegram Bot

```bash
cd backend
export TELEGRAM_BOT_TOKEN="你的Token"
python bot.py
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/simulate` | 主推演接口 (multipart/form-data, SSE流式) |
| POST | `/api/simulate/json` | 非流式版本 |
| GET | `/api/health` | 健康检查 |
| GET | `/api/memory/stats?user_id=xxx` | 记忆统计 |
| GET | `/api/memory/list?user_id=xxx` | 记忆列表 |
| POST | `/api/memory/clear` | 清除记忆 |

## CORS 配置

后端已配置 `allow_origins=["*"]`，前端通过 Next.js rewrites 代理请求。

## 推演系统架构

```
用户输入 → FormData (文本+图片)
    ↓
FastAPI main.py (/api/simulate)
    ↓
CognitiveEngine.simulate_stream()
    ├── MemoryManager.search() — 检索历史记忆
    ├── MemoryManager.get_user_profile() — 用户画像注入 System Prompt
    ├── OpenAI Vision 格式 messages 构建
    └── DeepSeek 流式 API 调用
    ↓
SSE Stream → 前端 ReadableStream → react-markdown 渲染
```
