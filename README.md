# 认知破壁机 · Cognitive Wallbreaker

AI 多智能体对抗推演引擎 — 五刀解剖 + 魔鬼代言人 + 终审法官 + 拓扑沙盘

[![Gitee](https://img.shields.io/badge/Gitee-bear__knowledge-red)](https://gitee.com/bear-knowledge/cognitive-wallbreaker)
[![GitHub](https://img.shields.io/badge/GitHub-IEVC--COUNT-blue)](https://github.com/IEVC-COUNT/cognitive-wallbreaker)

---

## 是什么

一个 AI 决策推演工具——输入你的个人决策（跳槽/买房/投资/感情/创业），七 Agent 进行对抗式深度推演，可视化拓扑沙盘展示决策衍生分支。

## 项目结构

```
cognitive-wallbreaker/
├── README.md
├── .env.example
├── docker-compose.yml            ← Docker 一键部署
├── 启动.cmd / 停止.cmd            ← Windows 快捷脚本
├── start-backend.bat
├── start-frontend.bat
│
├── backend/
│   ├── main.py                   ← FastAPI 后端 (端口 8920)
│   ├── engine.py                 ← V4.0 单引擎推演
│   ├── engine_v5.py              ← V5.0 多Agent 编排引擎
│   ├── prompts_v5.py             ← 7 Agent 专属 System Prompt
│   ├── public_api.py             ← 公共推演平台 API
│   ├── database.py               ← SQLite 数据库
│   ├── data_miner.py             ← 多平台事件采集管道
│   ├── history_manager.py        ← 推演历史记录
│   ├── memory_manager.py         ← 用户长期记忆
│   ├── bot.py                    ← Telegram Bot
│   ├── ocr_helper.js             ← 图片 OCR
│   ├── requirements_v2.txt       ← Python 依赖
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx              ← 主页面 (输入+输出+拓扑)
│   │   ├── layout.tsx            ← 根布局
│   │   └── globals.css           ← 全局样式 + 动画
│   ├── components/
│   │   ├── EventCard.tsx         ← 事件卡片
│   │   ├── ForumPanel.tsx        ← 论坛对话面板
│   │   ├── GlowNode.tsx          ← ReactFlow 发光节点
│   │   ├── ImageUploader.tsx     ← 图片拖拽上传
│   │   ├── MarkdownOutput.tsx    ← Markdown 渲染
│   │   └── TopologyViewer.tsx    ← 拓扑沙盘
│   ├── hooks/
│   │   └── useWallbreaker.ts     ← 核心推演 Hook
│   ├── types/
│   │   └── dagre.d.ts            ← TypeScript 类型声明
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── package.json
│   └── Dockerfile
│
└── data/
    ├── public.db                 ← SQLite 公共事件库
    ├── history/                  ← 历史记录 JSON
    └── memory/                   ← 用户记忆 JSON
```

## 快速启动

### Docker（推荐）

```bash
cp .env.example .env
docker compose up -d
# → http://localhost:3000
```

### 手动

```bash
# 后端
cd backend && pip install -r requirements_v2.txt
python main.py    # → http://localhost:8920

# 前端
cd frontend && npm install && npm run dev    # → http://localhost:3000
```

## 功能

### 推演模式

| 模式 | 说明 | Agent |
|------|------|-------|
| **单路 (V4.0)** | 五刀推演 + 拓扑沙盘 | 1次LLM |
| **双路 (Dual)** | 乐观 vs 悲观 两路并行 | 2次LLM |
| **七Agent (V5.0)** | 魔鬼代言人 + 终审法官 | 7次LLM |

### 交互

| 功能 | 说明 |
|------|------|
| 拓扑沙盘 | 6色发光节点 + dagre自动布局 |
| 光点点击 | 弹出节点详情卡 |
| 路径延伸 | 拓扑内推演不替换主输出，可关闭 |
| 双路独立延伸 | A/B两路各自延伸，宽度均匀 |
| 历史记录 | 侧边栏查看/回放/删除 |

### Agent 编排

```
阶段1 [并行]: 🔪心理刀 + 💰利益刀 + 📊阶层刀
阶段2 [串行]: ♟️博弈刀 → 💀灵魂刀
阶段3 [串行]: 😈魔鬼代言人 逐刀拆台
阶段4 [串行]: ⚖️首席推演官 终审判决 + 拓扑沙盘
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/simulate` | V4.0 单引擎推演 (SSE) |
| POST | `/api/simulate/v5` | V5.0 七Agent推演 (SSE) |
| POST | `/api/simulate/v5/fast` | V5.0 三Agent快速 (SSE) |
| POST | `/api/simulate/dual` | 双路对比推演 (SSE) |
| POST | `/api/public/submit` | 公共提交推演 |
| GET | `/api/public/events` | 事件列表 |
| GET | `/api/public/events/{id}` | 事件详情 |
| POST | `/api/public/events/{id}/outcome` | 现实反馈 |
| POST | `/api/public/mine` | 触发数据采集 |
| GET | `/api/health` | 健康检查 |

## 环境变量

| 变量 | 必填 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | ✅ | - |
| `OPENAI_BASE_URL` | ✅ | `https://api.deepseek.com/v1` |
| `WALLBREAKER_MODEL` | - | `deepseek-chat` |
| `V5_AGENT_TIMEOUT` | - | `45` |
| `TELEGRAM_BOT_TOKEN` | - | - |

## 技术栈

FastAPI + Next.js 14 + React 18 + ReactFlow + Tailwind CSS + dagre + SQLite + Docker
