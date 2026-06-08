# 认知破壁机 · Cognitive Wallbreaker V5.1

AI 多智能体对抗推演引擎 — 危机预见 + 五刀解剖 + 魔鬼代言人 + 终审法官 + 拓扑沙盘

[![Gitee](https://img.shields.io/badge/Gitee-bear__knowledge-red)](https://gitee.com/bear-knowledge/cognitive-wallbreaker)
[![GitHub](https://img.shields.io/badge/GitHub-IEVC--COUNT-blue)](https://github.com/IEVC-COUNT/cognitive-wallbreaker)

---

## 是什么

一个 AI 决策推演工具。输入你的决策（跳槽/买房/投资/感情/创业），**8 个 Agent** 进行对抗式深度推演，可视化拓扑沙盘展示决策衍生分支。

V5.1 新增 **🔭 危机预见官**——在五刀之前扫描用户忽略的隐藏危机维度，实现从"被动推演"到"主动发现未知风险"的升级。

## V5.1 架构

```
用户输入
    │
    ▼
┌─────────────────────────────┐
│ 🔭 阶段 0: 危机预见官       │  前置扫描：发现隐藏危机维度
│   · 用户问题框架盲区         │  外部变量 / 连锁反应 / 危机建议
│   · 被忽略的外部变量         │
│   · 潜在连锁反应             │
└──────────┬──────────────────┘
           │ 危机扫描结果注入后续 Agent
           ▼
┌─────────────────────────────┐
│ 🔪 阶段 1 [串行]: 三刀       │
│   心理防御解剖师             │  认知偏差、自欺信号
│   利益链条侦察员             │  庄家识别、收割链路
│   风险精算师                │  阶层容错率、底线压力测试
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ ♟️ 阶段 2 [串行]: 博弈策略师  │  止损策略、规则漏洞、反向操作
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ 💀 阶段 3 [串行]: 灵魂拷问者  │  直击回避真相的致命问题
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ 😈 阶段 4: 魔鬼代言人        │  逐刀反驳、指出漏洞和偏见
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ ⚖️ 阶段 5: 首席推演官        │  终审判决 + 行动优先级 + 拓扑沙盘
└─────────────────────────────┘
```

**特点**：魔鬼代言人对每刀独立反驳，法官无权输出新观点只能审判——这是 **真正的对抗推演**，不是流水线总结。

## 项目结构

```
cognitive-wallbreaker/
├── README.md
├── .env.example                  ← 环境变量模板
├── .env                          ← 本地配置（gitignore）
├── docker-compose.yml            ← Docker 一键部署
├── 启动.cmd / 停止.cmd            ← Windows 快捷脚本
├── start-backend.bat
├── start-frontend.bat
│
├── backend/
│   ├── main.py                   ← FastAPI 后端入口 (端口 8920)
│   ├── engine.py                 ← V4.0 单引擎推演
│   ├── engine_v5.py              ← V5.1 多Agent 编排引擎 (8 Agent)
│   ├── prompts_v5.py             ← 8 Agent 专属 System Prompt
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
│   │   ├── page.tsx              ← 主页面 (输入+输出+拓扑+Agent面板)
│   │   ├── layout.tsx            ← 根布局
│   │   └── globals.css           ← 全局样式 + 15组动画
│   ├── components/
│   │   ├── EventCard.tsx         ← 事件卡片
│   │   ├── ForumPanel.tsx        ← 8 Agent 实时论坛面板
│   │   ├── GlowNode.tsx          ← ReactFlow 发光节点
│   │   ├── ImageUploader.tsx     ← 图片拖拽上传
│   │   ├── MarkdownOutput.tsx    ← Markdown 流式渲染
│   │   └── TopologyViewer.tsx    ← 拓扑沙盘
│   ├── hooks/
│   │   └── useWallbreaker.ts     ← 核心推演 Hook + dagre 布局
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
# 编辑 .env 填入 API 密钥（或使用默认 DeepSeek 配置）
docker compose up -d
# → 前端 http://localhost:3000
# → 后端 http://localhost:8920
# → API 文档 http://localhost:8920/docs
```

### 手动

```bash
# 后端
cd backend
pip install -r requirements_v2.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8920

# 前端
cd frontend
npm install
npm run dev    # → http://localhost:3000
```

## 推演模式

| 模式 | Agent 数 | 说明 |
|------|---------|------|
| **单路 (V4.0)** | 1 | 五刀推演 + 拓扑沙盘，单次 LLM 调用 |
| **V5.1 完整** | 8 | 危机预见 + 五刀 + 魔鬼 + 法官，8 次 LLM |
| **V5.1 快速** | 4 | 危机预见 + 心理 + 利益 + 法官，4 次 LLM |
| **双路 (Dual)** | 2 | 乐观路径 vs 悲观路径并行推演 |

## Agent 清单 (V5.1)

| # | Agent | 职责 |
|---|-------|------|
| 🔭 | 危机预见官 | 前置扫描，发现用户忽略的隐藏危机维度 |
| 🔪 | 心理防御解剖师 | 认知偏差、自欺信号、情绪代偿 |
| 💰 | 利益链条侦察员 | 庄家识别、收割链路、社会规训 |
| 📊 | 风险精算师 | 阶层容错率、底线压力测试、恢复成本 |
| ♟️ | 博弈策略师 | 止损策略、规则漏洞、最小代价试错 |
| 💀 | 灵魂暴击拷问者 | 一个让用户沉默 3 秒的定制化拷问 |
| 😈 | 魔鬼代言人 | 逐刀反驳，寻找逻辑漏洞和偏见 |
| ⚖️ | 首席推演官 | 终审判决 + 行动优先级 + 拓扑沙盘生成 |

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/simulate` | V4.0 单引擎推演 (SSE) |
| POST | `/api/simulate/v5` | V5.1 八Agent推演 (SSE) |
| POST | `/api/simulate/v5/fast` | V5.1 四Agent快速 (SSE) |
| POST | `/api/simulate/dual` | 双路对比推演 (SSE) |
| POST | `/api/public/submit` | 公共提交推演 |
| GET | `/api/public/events` | 事件列表 |
| GET | `/api/health` | 健康检查 |
| GET | `/api/history/*` | 历史 CRUD |

## SSE 事件类型

| 事件 | 说明 |
|------|------|
| `phase` | 引擎阶段切换（memory/crisis/blades/…） |
| `agent_done` | 单个 Agent 完成，含完整文本 |
| `agent_error` | Agent 异常（API 超时/连接错误等） |
| `topology` | 拓扑沙盘 JSON 数据 |
| `done` | 全部推演完成 |
| `error` | 引擎级错误 |

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

## 交互功能

| 功能 | 说明 |
|------|------|
| 拓扑沙盘 | 6 色发光节点 + dagre 自动布局 + MiniMap + Controls |
| 光点点击 | 弹出节点详情卡 |
| 双击下钻 | What-If 路径延伸推演，不替换主输出 |
| 双路对比 | 乐观 A vs 悲观 B，各自独立延伸 |
| 历史记录 | 侧边栏查看/回放/删除 |
| 图片上传 | 拖拽上传 5 张图片（PNG/JPEG/WebP） |
| Agent 实时面板 | 8 Agent 状态动画：pending→running→done→error |
| 魔鬼震荡 | 魔鬼代言人拆台时边框震动动画 |
| 法官彩虹 | 终审判决完成时彩虹边框动画 |

## 设计系统

- **暗色赛博朋克主题**：深空蓝黑底 `#080c14` + 靛紫光 `#818cf8`
- **15 组 CSS 动画**：呼吸灯、粒子漂移、扫描线、彩虹边框、魔鬼震荡、裁决揭晓、节点发光…
- **字体**：Inter + Noto Sans SC（Google Fonts）
- **节点 6 色分类**：core / risk / safe / social / psychology / future
