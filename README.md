# 认知破壁机 · Cognitive Wallbreaker V6.0

公共个人决策推演平台 — 提交决策，多Agent公开推演，所有人可浏览学习

[![Gitee](https://img.shields.io/badge/Gitee-bear__knowledge-red)](https://gitee.com/bear-knowledge/cognitive-wallbreaker)
[![GitHub](https://img.shields.io/badge/GitHub-IEVC--COUNT-blue)](https://github.com/IEVC-COUNT/cognitive-wallbreaker)

---

## 是什么

一个**免登录**的公共决策推演平台。任何人打开浏览器就能：

- 📝 提交自己的个人决策（跳槽/买房/投资/感情/创业…）
- 🔪 让 AI 多Agent 进行对抗式深度推演
- 🌍 浏览所有人的推演案例，看别人怎么决策
- 📊 查看拓扑沙盘可视化，点节点继续推演
- ✅ 回来标记现实结果，对比 AI 推演准确度

## 架构概览

```
用户提交决策 "要不要裸辞创业"
    ↓
🌐 搜索注入 ← 自动搜索相关新闻/数据
🧠 匿名记忆 ← 累积用户历史决策模式
    ↓
┌──────────────────────────────────────────────────┐
│  V6.0 多智能体对抗推演引擎                         │
│                                                  │
│  阶段1 [并行]  🔪心理刀 + 💰利益刀 + 📊阶层刀      │
│  阶段2 [串行]  ♟️博弈刀 → 💀灵魂刀                │
│  阶段3 [串行]  😈魔鬼代言人 逐刀拆台                │
│  阶段4 [串行]  ⚖️首席推演官 终审判决 + 拓扑沙盘     │
└──────────────────────────────────────────────────┘
    ↓
SSE 流式输出 → 论坛对话面板 → 拓扑可视化 → 入库
    ↓
🌍 决策广场公开 → 📄 PDF导出 → ✅ 现实反馈
```

## 项目结构

```
cognitive-wallbreaker/
├── README.md
├── .env.example
├── docker-compose.yml            ← Docker 一键部署
├── 启动.cmd / 停止.cmd            ← 快捷脚本
│
├── backend/
│   ├── main.py                   ← FastAPI 后端 (端口 8920)
│   ├── engine.py                 ← V4.0 单引擎推演
│   ├── engine_v5.py              ← V5.0 多Agent 编排引擎
│   ├── prompts_v5.py             ← 7 Agent 专属 System Prompt
│   ├── public_api.py             ← V6.0 公共平台 API
│   ├── database.py               ← SQLite 数据库
│   ├── data_miner.py             ← 多平台事件采集管道 🆕
│   ├── history_manager.py        ← 推演历史记录
│   ├── memory_manager.py         ← 用户长期记忆
│   ├── bot.py                    ← Telegram Bot
│   ├── ocr_helper.js             ← 图片 OCR
│   ├── requirements_v2.txt       ← Python 依赖
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx              ← 决策广场首页
│   │   ├── layout.tsx            ← 根布局 + 导航栏
│   │   ├── globals.css           ← 全局样式 + 动画 + 打印样式
│   │   ├── submit/page.tsx       ← 提交推演页
│   │   └── event/[id]/page.tsx   ← 推演详情页
│   ├── components/
│   │   ├── EventCard.tsx         ← 广场卡片组件
│   │   ├── ForumPanel.tsx        ← 论坛对话面板 🆕
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
cp .env.example .env   # 编辑填入 API 密钥
docker compose up -d    # 一条命令启动
# → 前端 http://localhost:3000
# → 后端 http://localhost:8920
# → 文档 http://localhost:8920/docs
```

### 手动启动

```bash
# 后端
cd backend && pip install -r requirements.txt
python main.py    # → http://localhost:8920

# 前端
cd frontend && npm install && npm run dev    # → http://localhost:3000
```

## 三页面

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | 决策广场 | 所有推演案例卡片网格，最新/最热排序 |
| `/submit` | 提交推演 | 输入决策，选 V4/V5 模式，实时推演 |
| `/event/[id]` | 推演详情 | 完整结果 + 拓扑沙盘 + 现实反馈 |

## API 接口

### 公共推演平台（V6.0）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/public/submit` | 提交决策 + 推演 + 入库 (SSE) |
| GET | `/api/public/events` | 事件列表（分页+排序） |
| GET | `/api/public/events/{id}` | 事件详情（含现实反馈） |
| POST | `/api/public/events/{id}/outcome` | 提交现实结果反馈 |
| POST | `/api/public/mine` | 触发多平台事件采集 🆕 |
| GET | `/api/public/mine/sources` | 查看数据源 🆕 |

### 原有推演端点（兼容保留）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/simulate` | V4.0 单引擎推演 |
| POST | `/api/simulate/json` | V4.0 非流式 |
| POST | `/api/simulate/v5` | V5.0 7 Agent 推演 |
| POST | `/api/simulate/v5/fast` | V5.0 3 Agent 快速 |
| POST | `/api/simulate/dual` | 双路对比推演 |

### 管理与查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/history/list` | 历史记录 |
| GET | `/api/history/{id}` | 记录详情 |
| DELETE | `/api/history/{id}` | 删除记录 |
| GET | `/api/memory/stats` | 记忆统计 |
| GET | `/api/memory/list` | 记忆列表 |
| POST | `/api/memory/clear` | 清除记忆 |

## V6.0 核心特性

| 特性 | 说明 |
|------|------|
| 🔍 **搜索注入** | 推演前自动搜索现实背景信息，Agent 基于真实数据推演 |
| 😈 **论坛面板** | V5 模式实时可视化七Agent对话记录，点开展示完整文本 |
| 📄 **PDF导出** | 详情页一键打印/导出，自动隐藏UI只保留报告内容 |
| 🌍 **现实反馈** | 用户标记真实结果+AI准确度评分，公开对比学习 |
| 🧠 **匿名记忆** | localStorage 跨会话用户画像，无需注册，累积记忆 |
| 🛰 **事件采集** | 自动从 Reddit+V2EX 采集真实决策案例，LLM筛选后推演 |
| 📊 **拓扑沙盘** | ReactFlow 6色发光节点 + dagre 布局 + What-If 分支 |
| 🔪 **七Agent对抗** | 魔鬼代言人拆台 + 终审法官判决 |

## 数据采集

```
POST /api/public/mine?max_per_source=5

数据源:
  Reddit: r/ShouldI + r/makemychoice + r/Advice
  V2EX:   最新讨论

流程: 采集 → LLM筛选决策 → 自动推演 → 入库 → 广场展示
```

## 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| `OPENAI_API_KEY` | ✅ | OpenAI 兼容 API 密钥 | - |
| `OPENAI_BASE_URL` | ✅ | API 地址 | `https://api.deepseek.com/v1` |
| `WALLBREAKER_MODEL` | - | 模型名称 | `deepseek-chat` |
| `V5_AGENT_TIMEOUT` | - | Agent 超时秒数 | `45` |
| `TELEGRAM_BOT_TOKEN` | - | Telegram Bot | - |

## 技术栈

- **后端**: FastAPI + Uvicorn + OpenAI SDK (Async) + SQLite
- **前端**: Next.js 14 + React 18 + ReactFlow + Tailwind CSS + dagre
- **可视化**: ReactFlow 拓扑图 (自定义发光节点, 6 色类型, dagre 自动布局)
- **部署**: Docker Compose (Python 3.12 + Node.js 20 Alpine)
