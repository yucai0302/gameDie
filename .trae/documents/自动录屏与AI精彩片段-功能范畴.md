# 自动录屏 + AI 精彩片段生成 — 功能范畴定义

> Version：1.0
>
> 状态：范畴已确定，待实现
>
> 关联：[复赛项目迭代plan.md](复赛项目迭代plan.md) P1 `hardbutmust` 章节

---

## 一、功能定位

GameDie 的核心卖点之一：玩家打完一场对局，自动获得带 AI 字幕/标题/封面的精彩片段，无需任何额外操作。

**演示亮点**：现场打一场 → 比赛结束 → Media 库里已有多段精彩片段（ACE / 多杀 / 死亡回放），带 AI 生成的标题和字幕。

---

## 二、触发与录屏控制

### 2.1 录制方案：ffmpeg 自实现（不依赖 OBS）

- **不依赖 OBS**，用 ffmpeg + gdigrab 自实现环形缓冲录屏。
- **捕获范围**：游戏窗口（gdigrab 按窗口标题）。
  - CS2 需"无边框窗口"模式（启动项 `-windowed -noborder` 或设置选择），自动检测并提示用户切换。
- **录制内容**：画面 + 系统音频（WASAPI loopback）。
- **编码**：硬件编码自动检测（nvenc / amf / qsv），降低 CPU 占用。

### 2.2 触发时机（基于现有 GSI 事件）

**关键澄清**：触发不是"游戏进程启动"，而是"对局进行中且玩家存活"。

| GSI 事件 | 动作 | 说明 |
|---|---|---|
| `match_start`（`map.phase → "live"`，对局开始） | **启动 ffmpeg 持续录屏**（环形缓冲，临时目录只留最近 N 秒） | 此时玩家必然存活 |
| `death`（玩家死亡，hp → 0） | **回捞保存死亡前 30s** + **暂停录屏** | 死亡回放片段 = 死亡前存活画面；死亡后观战阶段不录，省资源 |
| `respawn`（玩家复活，hp 0 → >0） | **恢复录屏** | 下回合开始，玩家存活 |
| `kill` 累计达 ACE(5) / 多杀(3+) | **回捞保存最近 30s**，继续录屏 | 玩家存活中的高光时刻 |
| `match_end`（`map.phase → "gameover"`） | **停止录屏** | 对局结束 |

### 2.3 挂载点（复用现有 hook）

| 挂载位置 | 文件 | 作用 |
|---|---|---|
| `Agent.on_match_event` | `agent/main.py:194` | 按 event_type 分流，挂载精彩事件触发 |
| `Agent.on_death` | `agent/main.py:85` | 死亡回捞 + 暂停录屏 |
| `Agent._start_adapter` | `agent/main.py:256` | 游戏启动（备用） |
| `Agent._stop_adapter` | `agent/main.py:283` | 游戏退出（备用） |
| `Agent.on_match_event` 的 `match_start` 分支 | `agent/main.py:220` | 启动录屏 |
| `Agent.on_match_event` 的 `match_end` 分支 | `agent/main.py:232` | 停止录屏 |

### 2.4 精彩事件判定依据（现有能力）

| 事件 | 判定 | 现有实现 |
|---|---|---|
| 死亡 | `death` 事件 | `gsi_server.py:430` |
| ACE | 单回合 5 杀 | `backend/ai_review.py:69` `_detect_ace` |
| 多杀 | 单回合 3+ 杀（ACE 标 5+） | `backend/ai_review.py:77` `_detect_multi_kills` |
| 每回合击杀数聚合 | 按 `event_type == "kill"` 的 `round_number` | `backend/ai_review.py:35` `_count_kills_per_round` |

**已知限制**：GSI 当前只订阅本地玩家，无 `allplayers`，拿不到"击杀了谁/是否爆头"。精彩判定靠累计击杀数推断，够用；若后续需更细判定需扩 GSI cfg 订阅字段（`gsi_server.py:688`）。

### 2.5 回捞时长

- 默认 30 秒，Settings 可配。
- 比赛级配置优先于全局配置。

---

## 三、审核

### 3.1 审核形态：比赛结束统一审核

- 不做事件即时弹卡片（避免打断游戏）。
- 比赛结束 → 本场所有候选片段进入 Media 库。
- 每个片段携带元数据：
  - 事件类型（death / ace / multi_kill）
  - 时间戳（对局内相对时间 + 绝对时间）
  - 回合号
  - 精彩程度（如多杀数 3/4/5）
  - 关联比赛 ID
- Media 库按比赛分组展示，**批量勾选保留**。
- 未保留的片段（临时目录中的）定期清理。

---

## 四、发布（本地 Media 库 + AI 生成）

### 4.1 阶段 A：本地 Media 库 + AI 生成

- 保留片段 → AI 自动生成：
  - **标题**（基于事件类型 + 比赛数据，如"ACE! 沙漠2 第12回合五杀"）
  - **简介**（一句话描述）
  - **字幕**（事件标注：时间戳 + "ACE!" / "3杀" / "死亡回放"，叠加在画面上）
  - **封面**（从片段中抽取关键帧，可叠加标题文字）
- 仅本地 Media 库，**不接任何平台 API**。
- Media 库 UI 预留"发布到抖音"按钮占位（阶段 B 启用）。

### 4.2 阶段 B：抖音发布（暂缓，等权限）

- 依赖：抖音开放平台应用注册 + "代替用户发布内容到抖音"权限申请（审核周期约 2-4 周）。
- 流程：
  1. Settings 新增"抖音发布"配置区（client_key / client_secret / 回调域）
  2. OAuth 2.0 扫码授权 → 存储 access_token / refresh_token / open_id
  3. `POST /api/douyin/v1/video/upload_video/` 上传视频
  4. `POST /api/douyin/v1/video/create_video/` 发布（带标题/话题/封面）
  5. 发布状态查询（审核中 / 已发布 / 失败）
- token 管理：access_token ~7200s 过期，需 refresh_token 续期。
- 注意事项：
  - OAuth redirect_uri 需在开放平台配置，localhost 支持性需实测（可能需内网穿透）。
  - 抖音发布后审核机制，带水印会被降权——AI 封面/字幕避免品牌水印。

---

## 五、明确不做（控制范围）

| 不做项 | 原因 |
|---|---|
| 翻盘 / eco 翻盘判定 | 需多回合聚合，复杂度高 |
| AI 解说旁白字幕 | 先做事件标注字幕，旁白列为后续 |
| 多游戏适配 | 先 CS2，复用现有 adapter |
| 平台自动发布（B站/YouTube） | 阶段 B 仅抖音，其他平台后续 |
| 事件即时弹卡片审核 | 改为比赛结束统一审核，不打断游戏 |

---

## 六、现状基础（已具备）

| 能力 | 现状 |
|---|---|
| 事件采集 | GSI 产出 6 类事件（kill/death/round_start/round_end/match_start/match_end），带时间戳、回合号、详细 data |
| 事件流转 | `gsi_server` → `Agent.on_match_event`/`on_death` → 后端 SQLite + WebSocket → 前端 Timeline |
| 精彩判定 | `backend/ai_review.py` 已实现 ACE / 多杀识别 |
| 触发挂载点 | `agent/main.py` 的 `on_match_event` / `on_death` / `_start_adapter` / `_stop_adapter` |

| 缺失（需新建） |
|---|
| 录屏/视频/媒体库代码 0 实现，0 占位文件，0 依赖 |
| 无 Media 相关数据库表、路由、前端页面 |
| Timeline 不支持点击跳转录像（事件项无 onClick） |

---

## 七、架构独立性约束（重要）

本功能与现有功能（Dashboard / Timeline / Review / Gear / Settings）**完全独立**，避免互相影响。项目结构上分三层隔离。

### 7.1 前端独立

| 维度 | 现状 | 本功能做法 |
|---|---|---|
| 路由 | `/dashboard` `/timeline` `/review/:matchId` `/gear` `/settings` | **新增** `/media` 路由，不改动现有路由 |
| Tab 入口 | TopNav 4 个 tab（dashboard/timeline/settings/gear） | **新增** Media tab（图标 + i18n key），不改动现有 tab |
| 页面 | `pages/` 平铺 | **新增** `pages/Media.tsx`，独立页面 |
| 状态管理 | `store/useStore.ts` 单一 store | **新增** `store/mediaStore.ts` 独立 store slice，不污染现有 store |
| API 客户端 | `api/client.ts` | **新增** `api/mediaClient.ts` 独立模块，独立前缀 |
| 组件 | `components/` 平铺 | 新功能组件放 `components/Media/` 子目录，与现有组件物理隔离 |

**原则**：Media 模块的前端代码自成闭环，不 import 现有 Dashboard/Timeline 的业务组件；现有页面也不 import Media 的代码。

### 7.2 后端独立

| 维度 | 现状 | 本功能做法 |
|---|---|---|
| 路由 | `routers/` 平铺 7 个 router，统一 `/api` 前缀 | **新增** `routers/media.py`，独立 router，前缀 `/api/media` |
| 数据库 | `database.py` 平铺所有表 + `init_db()` | **新增** `media_database.py`，独立 init + 独立表（clips / clip_assets / media_settings），不在 `database.py` 里加表 |
| 业务逻辑 | 散落在 routers / ai_review.py | **新增** `services/recording_service.py`（录屏控制）、`services/clip_service.py`（片段管理）、`services/ai_clip_service.py`（AI 生成） |
| WebSocket | `state.py` 统一 manager，广播 `match_event` / `death` 等 | 复用 manager，但**新事件类型用独立前缀**：`media_clip_ready` / `media_recording_status`，不与现有事件混淆 |
| 挂载 | `main.py` `app.include_router(...)` | **新增** `app.include_router(media_router, prefix="/api/media")`，一行挂载 |

**原则**：后端 Media 模块独立文件、独立表、独立 service 层；现有 routers/database 不为 Media 改动任何代码（只在 `main.py` 加一行 include_router）。

### 7.3 Agent 侧独立

| 维度 | 现状 | 本功能做法 |
|---|---|---|
| 模块 | `agent/main.py` + `gsi_server.py` + `adapters/` + `ai_agents/` | **新增** `agent/recording/` 目录：`recorder.py`（ffmpeg 环形缓冲）、`controller.py`（事件→录屏控制）、`clip_extractor.py`（回捞片段） |
| 挂载方式 | `on_match_event` / `on_death` 内部分流 | **不改现有回调逻辑**，在 `Agent.__init__` 中注入 `RecordingController`，现有回调内**仅新增一行**调用 controller（如 `self.recorder.on_event(event)`） |
| 配置 | `agent/config.py` | 录屏配置独立到 `agent/recording/config.py` |

**原则**：录屏模块是可插拔的——即使 `agent/recording/` 整个目录删除，现有 Agent 也能正常运行（只需移除那行注入）。录屏失败不影响事件采集、复盘等现有功能。

### 7.4 独立性自检标准

实现完成后需满足：
1. 删除 `frontend/src/pages/Media.tsx` + `store/mediaStore.ts` + `api/mediaClient.ts` + `components/Media/` → 现有前端正常编译运行
2. 删除 `backend/routers/media.py` + `media_database.py` + `services/` 并移除 `main.py` 一行 include → 现有后端正常启动
3. 删除 `agent/recording/` 并移除 `main.py` 一行注入 → Agent 正常采集事件、上报、复盘
4. 录屏模块任何一步失败（ffmpeg 崩溃 / 片段提取失败 / AI 生成失败）→ 不影响现有 GSI 采集、Timeline、Review

---

## 八、分阶段实施

### 阶段 A（本次实现，与录屏同步）
- [ ] **Agent** `agent/recording/` 独立模块：ffmpeg 环形缓冲录屏 + 事件触发控制
- [ ] **Agent** 在 `on_match_event` / `on_death` 注入一行调用（不改现有逻辑）
- [ ] **后端** `routers/media.py` + `media_database.py` 独立表 + `services/` 独立业务层
- [ ] **后端** `main.py` 加一行 `include_router`，WebSocket 用 `media_*` 事件前缀
- [ ] **前端** `pages/Media.tsx` + `store/mediaStore.ts` + `api/mediaClient.ts` + `components/Media/`
- [ ] **前端** TopNav 新增 Media tab + `/media` 路由
- [ ] AI 生成标题/简介/字幕(事件标注)/封面
- [ ] Settings 录屏配置（回捞时长、编码器、捕获窗口）— 可放在 Media 页内独立配置区，不混入现有 Settings

### 阶段 B（暂缓，等抖音权限审核）
- [ ] 抖音开放平台应用注册 + 权限申请
- [ ] 抖音配置区 + OAuth 授权（在 Media 页内独立区域）
- [ ] 上传 + 发布 + 状态查询
- [ ] token 自动刷新

---

## 九、待定的技术细节（实现方案阶段细化）

- ffmpeg 环形缓冲的具体实现方式（分段录 + 滑动窗口 / 单进程 + segment muxer）
- 硬件编码器检测与降级策略
- 游戏窗口标题识别（与现有 `detector.py` 进程检测复用，但只读不依赖）
- 片段临时存储路径与清理策略
- AI 字幕叠加方式（ffmpeg drawtext / 烧录 vs 软字幕）
- 封面抽取与标题文字叠加
- Media 库独立数据库表结构（clips / clip_assets / media_settings）
- Media 库前端路由与组件设计
