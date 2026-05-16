# DIY旅游定制助手——开发任务拆分

**基于：PRD_v6.md + prd-review-panel 评审结论**
**核心原则：先骨架后血肉 | 每个任务独立可验收 | 任务间接口连通**

---

## 🎯 版本策略：MLP → 完整形态

本项目的开发分两层：

```
┌─────────────────────────────────────────────┐
│ MLP（最小可爱产品）: T1 → T2 → T3 → T4 → T5 → T6 → T7 │
│ 高德数据 + 距离矩阵 + 规划引擎 + 卡片 + 对话 + 行程     │
│ 不含 Bing 摘要/图片管道                               │
│ 预估 44~52h，完成后即可使用                           │
├─────────────────────────────────────────────┤
│ 完整形态（锦上添花）: MLP + T8 + T9 + T10             │
│ Bing 搜索摘要 + 游客实拍图片 + 动效打磨                │
│ 预估额外 11~15h                                     │
└─────────────────────────────────────────────┘
```

**为什么 MLP 不含 T8/T9？**

| 原因 | 说明 |
|------|------|
| 评审共识 | prd-review-panel 结论：摘要和图片是「血肉」非「骨架」 |
| Windows 限制 | `browser_use` 在 Windows headless 环境不稳定，Chrome 进程易残留、偶发崩溃 |
| Bing 搜索管道不可靠 | 80 次自动化搜索易触发验证码，调试成本高于收益 |
| 高德数据够用 | 评分 + 标签 + 费用同样能帮助用户判断（不输大众点评卡片） |
| MLP 已完整 | 刷卡 → 对话 → 规划 → 调整，核心流程不缺任何一环 |

### MLP 下的卡片替代方案

POI 卡片在无摘要/无图片时的展示：

```
┌──────────────────────────────────┐
│                                  │
│   [纯色封面 + POI 名称水印]       │  ← 替代：高德 tags 拼成摘要
│   骑行 · 日出 · 拍照              │
│                                  │
│   洱海生态廊道                    │
│   ⭐ 4.5 | 景点 | 1280 人评      │
│   骑行 · 日出 · 拍照 · 免费       │  ← 高德标签替代 LLM 摘要
│   🕐 2~3h  💰 ¥50~100           │
└──────────────────────────────────┘
```

---

## 任务总览

```
MLP（必做）:
T1 数据基石 → T2 后端骨架 → T3 规划引擎 → T4 前端卡片
                                            ↘
                                    T5 约束收集 → T6 全流程串联
                                                    ↘
                                            T7 行程展示与调整
                                                    ↓
                                            🎯 产品可交付使用

完整形态（选做，MLP 完成后再考虑）:
T8 摘要管道 ──→ T9 图片管道 ──→ T10 打磨
```

---

## T1：数据基石（高德 POI + 距离矩阵 + SQLite）

**做什么：**
- 跑高德 POI 采集脚本，拿到大理 80~120 个 POI
- 构建 `poi_cache.db`（含 City + POI 两张表）
- 跑高德路径规划 API，构建 `distance.db`（POI 对距离矩阵）
- 写一个 Python 脚本验证数据完整性

**验收标准：**
```
$ python check_data.py
City: 大理 (DL_001), POI 数量: 87
Distance matrix: 3,045/3,160 对已计算
抽样: 洱海生态廊道 → 寂照庵, 驾车 23min, 公交 45min  ✅
```

**产出文件：**
```
D:\X_PLAN\travel_agent\data\
├── poi_cache.db          ← 80~120 条 POI
├── distance.db           ← ~3000 条距离记录
├── pipeline_amap_fetch.py
├── pipeline_distance.py
└── check_data.py
```

**接 T2：** 提供 SQLite 数据库文件路径 + 数据模型，后端直接读。

**预估：** 4~6 小时（含 API 调试）

---

## T2：后端骨架（FastAPI + 基础端点 + Agent 壳）

**做什么：**
- FastAPI 项目初始化，目录结构
- `/api/v1/city/{city_name}` — 城市信息
- `/api/v1/poi/cards?session_id=` — 返回 POI 卡片列表（摘要用高德 tags 拼接）
- `/api/v1/poi/{poi_id}/score` — 保存评分
- `/api/v1/session` — 创建/恢复会话
- LangChain Agent 空壳（能接收消息、返回固定回复）
- SQLite 读写封装（`user.db` 建表）

**验收标准：**
```
$ curl http://localhost:8000/api/v1/city/大理
{"city_id":"DL_001","name":"大理","poi_count":87}

$ curl http://localhost:8000/api/v1/poi/cards?session_id=test
{"cards":[{"name":"洱海生态廊道","rating":4.5,"tags":["骑行","日出","拍照"],...},{...},{...}]}
```

**产出文件：**
```
backend/
├── main.py                ← FastAPI app
├── routers/
│   ├── city.py
│   ├── poi.py
│   └── session.py
├── db/
│   ├── connection.py      ← SQLite 连接管理
│   └── models.py          ← Pydantic models
├── agent/
│   └── main_agent.py      ← LangChain 空壳
└── requirements.txt
```

**接 T3：** 提供 `/api/v1/planner/run` 空端点，等 T3 的求解器接入。

**预估：** 4~6 小时

---

## T3：规划引擎（贪心 + 2-opt 求解器）

**做什么：**
- 实现贪心构造算法（天级分配）
- 实现 2-opt 局部优化（日内排序 + 交换）
- 查 `distance.db` 获取精确通勤时间
- 时间窗检查（营业时间、午餐/晚餐窗）
- 日容量检查（紧凑/休闲/标准）
- 降级策略（无解时标注原因）
- 接入 T2 的 `/api/v1/planner/run` 端点
- 写 5 个测试用例验证

**验收标准：**
```
$ curl -X POST http://localhost:8000/api/v1/planner/run -d '{"session_id":"xxx"}'
{
  "routes": [
    {"day":1, "pois":["古城","寂照庵","龙龛码头"], "total_cost":65},
    {"day":2, "pois":["双廊","喜洲"], "total_cost":120}
  ],
  "excluded": [{"name":"苍山","reason":"时间不足"}],
  "elapsed_ms": 3200
}
```

**产出文件：**
```
backend/
├── planner/
│   ├── solver.py           ← 贪心 + 2-opt 算法
│   ├── constraints.py      ← 时间窗/容量检查
│   ├── distance.py         ← 查 distance.db
│   └── test_planner.py     ← 5 个测试用例
```

**接 T4：** 提供规划 API，前端调用获得行程结果。

**预估：** 6~8 小时（算法调试占大头）

---

## T4：前端卡片流（React + TinderCard 滑动评分）

**做什么：**
- React + Vite + TypeScript 项目初始化
- 实现 POI 卡片组件（纯色封面 + 高德 tags 拼接摘要 + 评分 + 时长费用）
- 接入 `/api/v1/poi/cards`，每次拿 3 张
- react-tinder-card 集成：左滑=不感兴趣，右滑=想去
- 点击星级精确打分
- 进度指示（已看 X/30）
- 退出按钮（"开始排程"）
- 基础状态覆盖（Loading skeleton / Empty 提示）

**验收标准：**
打开浏览器 → 看到 3 张大理 POI 卡片 → 可左滑右滑 → 进度条走 → 点击"开始排程"跳转到占位页面。

**产出文件：**
```
frontend/
├── src/
│   ├── App.tsx
│   ├── pages/
│   │   ├── CardFlow.tsx        ← 卡片页面
│   │   └── Placeholder.tsx     ← 占位（接 T5）
│   ├── components/
│   │   ├── PoiCard.tsx         ← 单张卡片
│   │   ├── CardDeck.tsx        ← 3 张卡片堆叠
│   │   └── ProgressBar.tsx
│   ├── api/
│   │   └── client.ts           ← API 调用封装
│   └── store/
│       └── sessionStore.ts     ← zustand 状态
├── package.json
└── vite.config.ts
```

**接 T5：** 卡片流 → 点击"开始排程" → 跳转到约束收集页面。

**预估：** 8~12 小时（前端开发 + 联调）

---

## T5：约束收集（对话式逐步表单）

**做什么：**
- 前端对话式 UI：Agent 提问 → 用户输入框回答 → 下一个问题
- 后端 Agent 驱动：解析用户回答 → 智能推断 → 追问下一项
- 收集 8 项约束（人数、时间、住宿、交通、节奏、美食、预算、特殊需求）
- 约束冲突提示（如 3 天 12 个想去）
- 后端 `/api/v1/profile/{session_id}` 读写

**验收标准：**
```
用户点击"开始排程"
→ 💬 "几个人一起去呀？"
→ 用户输入"两个人"
→ 💬 "你们两个人一起去对吗？第一天几点到大理？"
→ ... 8 轮对话 ...
→ 💬 "好嘞，都记下了！开始帮你规划路线~"
→ 跳转到规划等待页
```

**产出文件：**
```
frontend/src/pages/
├── ConstraintChat.tsx     ← 对话式 UI
frontend/src/components/
├── ChatBubble.tsx         ← 聊天气泡
├── QuickReply.tsx         ← 快捷回复按钮（"休闲" / "紧凑"）
backend/agent/
├── constraint_agent.py    ← 约束收集逻辑（提问策略 + 推断规则）
```

**接 T6：** 约束收集完成 → 触发规划引擎 → 展示行程。

**预估：** 5~7 小时

---

## T6：全流程串联（端到端打通）

**做什么：**
- 约束收集完成 → 自动调用 `/api/v1/planner/run`
- 规划完成 → 前端跳转到行程展示页
- 前端路由串联：`/city` → `/cards` → `/constraint` → `/planning` → `/result`
- Session 全生命周期管理（创建→卡片流→约束→规划→结果）
- 浏览器关闭后恢复（Session ID 存 localStorage）
- 端到端测试：完整走一遍

**验收标准：**
打开浏览器 → 输入大理 3 天 → 刷卡 10 张 → 回答 8 个约束 → 10 秒内看到 3 天行程时间线。

**产出文件：**
```
frontend/src/
├── App.tsx                 ← 路由串联
├── pages/
│   ├── CityInput.tsx       ← 目的地输入
│   ├── PlanningWait.tsx    ← 规划中等待动画
│   └── Result.tsx          ← 行程展示（接 T7）
backend/agent/
├── orchestrator.py         ← 状态机调度
```

**预估：** 3~5 小时

---

## T7：行程展示与调整

**做什么：**
- 时间线视图（每日上午/中午/下午/晚上）
- 费用汇总 + 通勤统计
- 放弃 POI 列表 + 原因标注
- 删除 POI → 增量重规划
- 添加 POI → 候选列表 → 重规划
- 调整节奏/预算 → 全量重规划
- 被放弃 POI 的"加回来"操作

**验收标准：**
看到完整 3 天行程 → 点 × 删除寂照庵 → 自动补入待选 POI → 点 + 添加苍山 → 路线重新生成 → 切换"紧凑模式"→ 日程变满。

**产出文件：**
```
frontend/src/
├── pages/
│   └── Result.tsx            ← 完整行程页
├── components/
│   ├── TimelineDay.tsx       ← 单日时间线
│   ├── TimelineItem.tsx      ← 单个 POI 条目
│   ├── ExcludedPanel.tsx     ← 未安排列表
│   └── AdjustmentBar.tsx     ← 顶部调整工具栏
backend/planner/
├── adjust.py                 ← 增量重规划逻辑
```

**预估：** 6~8 小时

---

## 🎯 MLP 工时汇总（T1~T7）

| 任务 | 预估工时 | 累计 | 可见成果 |
|------|---------|------|---------|
| T1 数据 | 4~6h | 6h | 数据库文件 |
| T2 后端 | 4~6h | 12h | API 可调 |
| T3 规划引擎 | 6~8h | 20h | API 返回路线 |
| T4 前端卡片 | 8~12h | 32h | 可刷卡 |
| T5 约束收集 | 5~7h | 39h | 对话式收集 |
| T6 全流程串联 | 3~5h | 44h | **端到端可用** ✅ |
| T7 行程调整 | 6~8h | 52h | **MLP 完成，可交付** 🎯 |

**MLP 总计：44~52 小时**

---

## 依赖关系与可并行任务

```
T1 ──→ T2 ──→ T3 ──→ T6 ──→ T7  🎯 MLP 完成
         │       │      ↑
         └──→ T4 ──→ T5 ──┘
```

**T4 和 T5** 可以在 T2 完成后跟 T3 并行做（前后端分离，接口约定好就行）。

---

## 给 Claude Code 的使用方式

每完成一个任务，把当前结果给曹Sir验一下，通过后再做下一个。

启动提示示例：
```
请根据 PRD_v6.md 的 §4（数据管道）和 §5（数据模型），
完成 T1 数据基石任务。要求：
1. 高德 POI 采集脚本，输出 poi_cache.db
2. 距离矩阵构建脚本，输出 distance.db
3. 数据完整性检查脚本
输出到 D:\X_PLAN\travel_agent\data\
```

> 每个任务一个 session，不串味，不迷路。

---

---

## ═══════════════════════════════════════
## 以下为完整形态扩展任务（MLP 完成后可选）
## ═══════════════════════════════════════

### T8：摘要管道（Bing 搜索 + LLM 提炼）`[可选·有风险]`

> ⚠️ **前置说明：** PRD 原设计使用 `browser_use` 在 headless Chrome 中爬取 Bing 搜索结果。实测 Windows headless 环境下 `browser_use` 不稳定（Chrome 进程残留、中文编码、GPU 崩溃），且 Bing 对自动化搜索易触发验证码。**建议 MLP 完成后根据实际需要再评估是否实施。**

**三个替代路径（届时选一）：**

| 路径 | 可靠性 | 成本 | 工作量 |
|------|--------|------|--------|
| A: Bing Search API (Azure 免费层 1000次/月) | ⭐⭐⭐⭐⭐ | 免费层 | 2~3h |
| B: 保持 MLP 方案（高德 tags 作摘要） | ⭐⭐⭐⭐⭐ | 零 | 0h |
| C: browser_use + headed 模式（需可见窗口） | ⭐⭐⭐ | 零 | 调试成本高 |

**如果选路径 A，做什么：**
- 注册 Azure 账号，开通 Bing Search API（免费层）
- 编写 `pipeline_bing_summary.py`，调 API 取搜索结果
- LLM 提炼 40 字摘要 → 写入 poi_cache.db
- 前端卡片替换摘要展示，标注来源平台

**产出文件（如实施）：**
```
data/
└── pipeline_bing_summary.py
```

---

### T9：图片管道（Bing 图片采集）`[可选·依赖 T8]`

> ⚠️ **同 T8，Windows headless browser_use 可靠性风险。**

**如果实施，做什么：**
- Bing 图片搜索：封面 1 张 + 画廊 4 张
- WebP 压缩（800×600 / 400×300）
- 前端卡片展示真实图片替换纯色封面
- swiper.js 左右滑动浏览画廊

**产出文件（如实施）：**
```
data/
├── pipeline_bing_images.py
└── images/DL_001/
```

---

### T10：打磨（动效 + 错误态 + 细节）`[可选]`

**做什么：**
- 卡片飞出/进入动画（framer-motion）
- 全量错误态覆盖（网络断开、API 超时、规划无解）
- 键盘操作（← → 键刷卡）
- 响应式适配（手机端也能用）
- 首屏加载优化

---

## 完整形态工时（含 MLP + T8~T10）

| 任务 | 预估工时 | 说明 |
|------|---------|------|
| MLP (T1~T7) | 44~52h | **必做，可交付** |
| T8 摘要管道 | 2~5h | 可选，取决于选择路径 A 或 B |
| T9 图片管道 | 3~4h | 可选，依赖 T8 |
| T10 打磨 | 4~6h | 可选，体验提升 |
| **完整形态总计** | **53~67h** | |
