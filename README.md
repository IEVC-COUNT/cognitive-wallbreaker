# 认知破壁机 · Cognitive Wallbreaker V5.0

AI 多智能体对抗推演引擎 — 七 Agent 辩论，魔鬼代言人挑刺，终审法官判决

## 架构概览

```
用户输入 (文本+图片)
    ↓
┌──────────────────────────────────────────────────┐
│  V5.0 多智能体对抗推演引擎                         │
│                                                  │
│  阶段1 [并行]  🔪心理刀 + 💰利益刀 + 📊阶层刀      │
│  阶段2 [串行]  ♟️博弈刀 → 💀灵魂刀                │
│  阶段3 [串行]  😈魔鬼代言人 逐刀拆台                │
│  阶段4 [串行]  ⚖️首席推演官 终审判决 + 拓扑沙盘     │
└──────────────────────────────────────────────────┘
    ↓
SSE 流式输出 → 前端 ReactFlow 拓扑可视化
```

## 项目结构

```
cognitive-wallbreaker/
├── README.md
├── .env.example
├── docker-compose.yml          ← Docker 一键部署
├── start-backend.bat
├── start-frontend.bat
├── backend/
│   ├── main.py                 ← FastAPI 后端 (端口 8920)
│   ├── engine.py               ← V4.0 单引擎推演
│   ├── engine_v5.py            ← V5.0 多Agent 编排引擎
│   ├── prompts_v5.py           ← 7 Agent 专属 System Prompt
│   ├── memory_manager.py       ← 用户长期记忆 (JSON 存储)
│   ├── history_manager.py      ← 推演历史记录
│   ├── ocr_helper.js           ← 图片 OCR (Node.js)
│   ├── requirements.txt        ← Python 依赖
│   ├── requirements_v2.txt     ← Python 依赖 (Docker 用)
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx            ← 主页面 (单路/双路/V5)
│   │   ├── layout.tsx          ← 根布局
│   │   └── globals.css         ← 全局样式 + 动画
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── Dockerfile
└── data/
    ├── history/                ← 推演历史 JSON
    └── memory/                 ← 用户记忆 JSON
```

## 快速启动

### Docker Compose 一键部署（推荐）

```bash
# 复制环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥

# 启动
docker compose up -d

# 后端: http://localhost:8920
# 前端: http://localhost:3000
# API 文档: http://localhost:8920/docs
```

### 手动启动

#### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入：
#   OPENAI_API_KEY=sk-你的密钥
#   OPENAI_BASE_URL=https://api.deepseek.com/v1
#   WALLBREAKER_MODEL=deepseek-chat
```

#### 3. 启动后端 API (端口 8920)

```bash
cd backend
python main.py
# → http://localhost:8920
# → API 文档: http://localhost:8920/docs
```

#### 4. 启动前端 (端口 3000)

```bash
cd frontend
npm install    # 首次运行
npm run dev
# → http://localhost:3000
```

## API 接口

### 推演端点

| 方法 | 路径 | 说明 | LLM 调用 |
|------|------|------|---------|
| POST | `/api/simulate` | V4.0 单引擎五刀推演 (SSE) | 1 次 |
| POST | `/api/simulate/json` | V4.0 非流式 JSON 版 | 1 次 |
| POST | `/api/simulate/v5` | V5.0 7 Agent 对抗推演 (SSE) | 7 次 |
| POST | `/api/simulate/v5/fast` | V5.0 3 Agent 快速模式 (SSE) | 3 次 |
| POST | `/api/simulate/dual` | 双路对比 — 乐观 vs 悲观 (SSE) | 2 次 |

### V5.0 完整版 Agent 编排

```
阶段1 [并行]: Agent 1+2+3 同时跑
  🔪 心理防御解剖师 — 认知偏差、自欺信号
  💰 利益链条侦察员 — 庄家识别、收割逻辑
  📊 风险精算师     — 阶层容错、底线测试

阶段2 [串行]: Agent 4 → Agent 5
  ♟️ 博弈策略师     — 读取前三刀 → 止损/反向操作
  💀 灵魂暴击拷问者 — 读取前四刀 → 致命提问

阶段3 [串行]: Agent 6
  😈 魔鬼代言人     — 逐刀反驳，找出漏洞偏见

阶段4 [串行]: Agent 7
  ⚖️ 首席推演官     — 终审判决 + 拓扑沙盘 JSON
```

### 管理与查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 + 端点列表 |
| GET | `/api/history/list?user_id=xxx` | 历史记录列表 |
| GET | `/api/history/{id}?user_id=xxx` | 单条推演详情 |
| DELETE | `/api/history/{id}?user_id=xxx` | 删除推演 |
| GET | `/api/memory/stats?user_id=xxx` | 记忆统计 |
| GET | `/api/memory/list?user_id=xxx` | 记忆列表 |
| POST | `/api/memory/clear` | 清除记忆 |

## SSE 事件类型

| 事件 | 说明 | 适用端点 |
|------|------|---------|
| `thinking` | 引擎状态更新 | V4.0 |
| `content_start` | 开始输出 | V4.0 |
| `content` | 增量文本 | V4.0, Dual |
| `phase` | 阶段切换 | V5.0 |
| `agent_done` | 单 Agent 完成 (含完整输出) | V5.0 |
| `agent_error` | 单 Agent 异常 | V5.0 |
| `meta` | 双路元信息 (路径标签) | Dual |
| `topology` | 拓扑沙盘 JSON | 全部 |
| `done` | 推演完成 | 全部 |
| `error` | 引擎级错误 | 全部 |
| `history_saved` | 历史已保存 | V4.0 |

## 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| `OPENAI_API_KEY` | ✅ | OpenAI 兼容 API 密钥 | - |
| `OPENAI_BASE_URL` | ✅ | API 地址 | `https://api.deepseek.com/v1` |
| `WALLBREAKER_MODEL` | - | 模型名称 | `deepseek-chat` |
| `V5_AGENT_TIMEOUT` | - | Agent 超时秒数 | `45` |
| `TELEGRAM_BOT_TOKEN` | - | Telegram Bot (可选) | - |

## 技术栈

- **后端**: FastAPI + Uvicorn + OpenAI SDK (Async)
- **前端**: Next.js 14 + React 18 + ReactFlow + Tailwind CSS + dagre
- **可视化**: ReactFlow 拓扑图 (自定义发光节点, 6 色类型, dagre 自动布局)
- **部署**: Docker Compose (Python 3.12 + Node.js 20 Alpine)
