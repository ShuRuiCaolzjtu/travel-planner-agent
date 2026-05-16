# 🧭 智旅行者 — 多日行程规划智能 Agent 系统

<p align="center">
  <strong>Travel Planner Agent</strong> — AI-Powered Multi-Day Itinerary Planner
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React%2019%20%7C%20TypeScript%20%7C%20Vite%208-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Backend-Python%20%7C%20FastAPI-green?style=flat-square" />
  <img src="https://img.shields.io/badge/AI-DeepSeek%20LLM-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Map-AMap%20JS%20API%202.0-red?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" />
</p>

---

## 🌟 项目简介

**智旅行者** 是一款 AI 驱动的多日行程规划助手。用户只需选择目的地和游玩天数，像刷短视频一样左右滑动景点卡片表达偏好，再跟 AI 旅行助手聊几句——告诉它几点到、几点走、住哪里、玩多累——系统就能在 **几秒内** 自动生成一份完整的每日行程单，附带高德地图驾车导航路线和每个景点的到达离开时间。

> 🎯 它把「查攻略 → 列清单 → 做路线」三个步骤压缩成一次轻松的**AI 对话**，全程无需填任何表单。

### ✨ 核心体验

| 步骤 | 交互方式 | 耗时 |
|------|---------|:----:|
| 🏙 **选择城市与天数** | 输入框直接输入 | < 5 秒 |
| 🃏 **偏好收集卡片流** | Tinder 式左右滑动打分 | 3~8 分钟 |
| 💬 **约束收集对话** | 跟 AI 旅行助手聊天 | 2~5 分钟 |
| 📋 **智能路径规划** | 自动求解 | < 10 秒 |
| 🗺 **地图展示与调整** | 高德驾车导航路线展示 | 实时 |

### 🏆 与竞品差异

| 维度 | 传统行程工具 | **智旅行者** |
|------|------------|------------|
| 输入方式 | 手动勾选景点 + 拖拽排序 | 🃏 刷卡片 + 💬 聊天 |
| 路线规划 | 用户自行判断是否顺路 | 🤖 2-opt 算法自动优化路径 |
| 动态调整 | 无法临时变更 | ✅ 支持增删改，秒级重规划 |
| 交互体验 | 表单填写 | 对话式、直觉化 |

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────┐
│  前端 — React SPA (Vite 8 + TypeScript)              │
│  ┌──────────┐ ┌──────────┐ ┌───────────────────┐    │
│  │ CardDeck │ │ ChatBox  │ │ RouteMap (AMap)  │    │
│  └──────────┘ └──────────┘ └───────────────────┘    │
│  状态管理: zustand | 路由: react-router v6            │
└──────────────────┬──────────────────────────────────┘
                   │ REST API (JSON)
┌──────────────────▼──────────────────────────────────┐
│  后端 — FastAPI (Python 3.12)                        │
│  ┌─────────────┐ ┌────────────┐ ┌──────────────┐    │
│  │ 路由层       │ │ Agent 层   │ │ 规划引擎      │    │
│  │ /api/v1/*   │ │ LangChain  │ │ 贪心+2-opt   │    │
│  └─────────────┘ └────────────┘ └──────────────┘    │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│  数据层 — SQLite 三库分离                              │
│  poi_cache.db (POI 数据)                             │
│  distance.db   (距离矩阵)                             │
│  user.db       (会话与偏好)                           │
└─────────────────────────────────────────────────────┘
```

### 核心设计原则

- ⚡ **全部离线预计算**：用户使用时毫秒级响应，无实时 API 调用
- 🤖 **LLM + 规则双引擎**：主通道 DeepSeek LLM，备通道 29 条正则规则自动降级
- 🗺 **高德地图集成**：真实驾车路网路径规划，支持缩放平移
- 🏭 **全国可复制**：数据采集管线一键适配全国任意城市

---

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+
- pnpm / npm / yarn

### 1. 克隆项目

```bash
git clone https://github.com/ShuRuiCaolzjtu/travel-planner-agent.git
cd travel-planner-agent
```

### 2. 后端启动

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 配置 DeepSeek API（可选，不配则使用规则兜底）
set LLM_API_KEY=your_deepseek_api_key_here

# 启动服务
uvicorn backend.main:app --reload --port 8000
```

API 文档访问：http://127.0.0.1:8000/docs

### 3. 前端启动

```bash
# 安装依赖
cd frontend
pnpm install

# 启动开发服务器
pnpm dev
```

浏览器打开 http://127.0.0.1:5173

### 4. 数据初始化（以大理为例）

```bash
cd data

# 第1步：高德POI采集
python pipeline_amap_fetch.py --city 大理

# 第2步：LLM二分类过滤
python pipeline_llm_filter.py --city 大理

# 第3步：距离矩阵计算（耗时较长）
python pipeline_distance.py --city 大理
```

---

## 📂 项目结构

```
travel-planner-agent/
├── backend/                  # FastAPI 后端
│   ├── agent/                # AI Agent 层
│   │   ├── main_agent.py     # 对话状态机
│   │   └── constraint_agent.py  # 约束收集 Agent (LLM+规则)
│   ├── db/                   # 数据库层
│   │   ├── connection.py     # SQLite 连接管理
│   │   └── models.py         # Pydantic 数据模型
│   ├── planner/              # 路径规划引擎
│   │   ├── solver.py         # 贪心+2-opt求解器
│   │   ├── constraints.py    # 约束处理器
│   │   ├── distance.py       # 距离查询
│   │   └── adjust.py         # 行程调整
│   ├── routers/              # API 路由
│   │   ├── city.py           # 城市信息
│   │   ├── poi.py            # POI 卡片
│   │   ├── session.py        # 会话管理
│   │   ├── planner.py        # 规划引擎
│   │   └── constraint.py     # 约束收集
│   ├── main.py               # 应用入口
│   └── requirements.txt
├── data/                     # 数据管线
│   ├── pipeline_amap_fetch.py    # 高德POI采集
│   ├── pipeline_llm_filter.py    # LLM二分类过滤
│   └── pipeline_distance.py      # 距离矩阵计算
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── api/client.ts     # API 客户端
│   │   ├── components/       # 通用组件
│   │   │   ├── CardDeck.tsx      # 卡片滑动组件
│   │   │   ├── PoiCard.tsx       # POI 卡片
│   │   │   └── RouteMap.tsx      # 高德地图组件
│   │   ├── pages/            # 页面
│   │   │   ├── CityInput.tsx     # 目的地输入
│   │   │   ├── CardFlow.tsx      # 卡片流
│   │   │   ├── ConstraintChat.tsx # 约束对话
│   │   │   └── ResultPage.tsx    # 行程结果
│   │   ├── store/            # zustand 状态管理
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
├── main.py                   # 项目入口
├── PRD_v6.md                 # 产品需求文档
└── README.md
```

---

## 🎯 交互流程

### 阶段 1：目的地输入
```
用户输入："我要去大理玩 3 天"
  → 系统查询城市数据库
  → "大理有 87 个去处，开始刷卡吧~"
```

### 阶段 2：卡片流偏好收集
```
┌──────────────────────────┐
│   [洱海生态廊道]          │
│   ⭐ 4.5 | 景点 | 1280人评│
│   "环湖骑行很舒服..."     │
│                          │
│   👈 跳过       想去 👉  │
└──────────────────────────┘
```

### 阶段 3：AI 约束收集对话
```
Agent: "几个人一起去呀？"
用户: "和女朋友两个人"
Agent: "好嘞~第一天几点到大理？"
用户: "早上 7 点到大理站"
...
```

### 阶段 4：路径规划与地图展示
```
📅 第 1 天 | 4个去处
  09:00  大理古城（住宿出发）
  11:30  再回首凉鸡米线
  13:00  寂照庵
  17:00  龙龛码头看日落
  
  🗺 [高德驾车导航路线图]
```

---

## 🏭 全国可复制

数据采集管线已实现端到端自动化，新城市仅需依次运行三个脚本：

```bash
python pipeline_amap_fetch.py --city 南京
python pipeline_llm_filter.py --city 南京
python pipeline_distance.py --city 南京
```

系统核心算法与城市无关，后端已将 `city_id` 作为一等参数传入所有接口。

**已测试城市：** 大理、南京、青岛（更多持续验证中）

---

## 🧠 核心技术

| 模块 | 技术 | 说明 |
|------|------|------|
| 前端框架 | React 19 + TypeScript + Vite 8 | 现代化 SPA 开发 |
| 地图渲染 | 高德地图 JS API 2.0 | 驾车导航路线、缩放平移 |
| 卡片交互 | react-tinder-card | 五种手势滑动 |
| 后端框架 | Python FastAPI | 高性能异步 Web 框架 |
| AI 引擎 | DeepSeek LLM | 约束收集 + 智能推断 |
| 规则引擎 | 29 条正则规则 | LLM 降级后备 |
| 路径规划 | 贪心 + 2-opt 局部优化 | 最小化通勤时间 |
| 存储 | SQLite 三库分离 | poi_cache / distance / user |

---

## 📄 License

[MIT License](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 PR！一起把旅行规划变得更简单。

---

<p align="center">
  Made with ❤️ — 一个想让你说走就走的项目
</p>
