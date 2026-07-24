# 小智积分系统架构设计（MOA: Multi-Agent Architecture）

## 现状痛点

| 问题 | 说明 | 风险 |
|------|------|------|
| **重复计分** | cloud_sync + live MCP 各自写 game_data.json，无去重 | 同一活动计两次 |
| **JSON 无事务** | 多进程并发写入导致数据撕裂 | 总积分偏差 |
| **Schema 不一致** | 有的记录用 `base`/`bonus`，有的用 `points`/`total` | 统计混乱 |
| **兑换扣分不透明** | 兑换后直接在 JSON 里改 total_score，缺乏审计日志 | 无法追溯 |
| **总分漂移** | `total_score = sum(history[*].total)` 手动维护，容易不一致 | 分数不准 |

## MOA 设计：三 Agent + 一存储

```
┌─────────────────────────────────────────────────────┐
│                   积分总线 (SQLite)                    │
│  ACID · 唯一约束 · 统一 Schema · WAL 并发              │
└──────────┬──────────────┬──────────────┬────────────┘
           │              │              │
     ┌─────▼─────┐  ┌────▼────┐  ┌─────▼─────┐
     │ Agent A   │  │ Agent B │  │ Agent C   │
     │ 语音采集  │  │ 云端同步 │  │ 兑换商店  │
     │ (实时)   │  │ (定时)  │  │ (消费)    │
     └───────────┘  └─────────┘  └───────────┘
```

---

## 1. 存储层：SQLite（替代 JSON）

### 为什么选 SQLite 不选 JSON

| 对比维度 | JSON | SQLite |
|---------|------|--------|
| 并发写入 | ❌ 同时写会撕裂 | ✅ WAL 模式，读写不互斥 |
| 数据去重 | ❌ 需代码检查 | ✅ UNIQUE(date, activity, source_id) |
| 事务支持 | ❌ 无 | ✅ BEGIN/COMMIT/ROLLBACK |
| 查询能力 | ❌ 全量加载 | ✅ SQL 过滤分页聚合 |
| Schema | ❌ 字段名不统一 | ✅ 统一列定义 |
| 依赖 | ✅ 内置 | ✅ Python 标准库 sqlite3 |
| 运维 | ✅ 直接编辑 | ⚠️ 需 SQL 或 GUI 工具 |

### 表结构设计

```sql
-- 1. 积分流水表（核心）
CREATE TABLE score_ledger (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,          -- '2026-07-24'
    activity    TEXT    NOT NULL,          -- 'english_quiz'
    points      INTEGER NOT NULL DEFAULT 0, -- 实际分值（正=收入，负=支出）
    label       TEXT    DEFAULT '',         -- 中文标签
    source      TEXT    NOT NULL DEFAULT 'voice',  -- voice|cloud_sync|cron|cli|redeem
    source_id   TEXT    DEFAULT NULL,       -- 去重ID（云端chat_id或消息ID）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    
    -- 防重复约束：同一来源的同一活动只计一次
    UNIQUE(date, activity, source_id)
);

-- 2. 兑换记录表
CREATE TABLE redemptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reward_id   TEXT    NOT NULL,
    reward_name TEXT    NOT NULL,
    cost        INTEGER NOT NULL,           -- 花费积分
    status      TEXT    NOT NULL DEFAULT 'pending',  -- pending|approved|rejected|cancelled
    requested_at TEXT   NOT NULL DEFAULT (datetime('now')),
    approved_at TEXT,
    approved_by TEXT,
    note        TEXT    DEFAULT ''
);

-- 3. 每日汇总（物化缓存，快速读取今日进度）
CREATE TABLE daily_summary (
    date        TEXT    PRIMARY KEY,
    total       INTEGER NOT NULL DEFAULT 0,
    activities  TEXT    NOT NULL DEFAULT '{}',  -- JSON: {"english_quiz":2, "exercise":1}
    multi_bonus INTEGER NOT NULL DEFAULT 0,
    streak_days INTEGER NOT NULL DEFAULT 0
);

-- 4. 全局状态（单行配置表）
CREATE TABLE global_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- 行示例: ('total_score', '697'), ('level', '学习小明星')
```

---

## 2. Agent A：语音采集（实时，现有）

**职责**：通过 MCP WebSocket 接收云端 AI 调用，实时记录活动积分。

**现有文件**：`xiaozhi_edu_client.js` → `edu_backend.py` → `game_engine.py`

**改造方案**：

```
MCP 调用 → edu_backend.py → game_engine.record_activity()
                                  │
                           ┌──────▼──────┐
                           │ SQLite 写入  │ ← 原子 INSERT，UNIQUE 防重
                           │ (WAL模式)    │
                           └──────┬──────┘
                                  │
                           ┌──────▼──────┐
                           │ JSON 同步    │ ← 异步刷新 game_data.json（向前兼容）
                           └─────────────┘
```

**防重复机制**：
- `UNIQUE(date, activity, source_id)` — 同一 chat_id 的同一活动只计一次
- Agent A 的 `source = 'voice'`, `source_id = 工具调用ID`

---

## 3. Agent B：云端同步（定时，新增）

**职责**：每天 23:00 从 xiaozhi 云端拉取聊天记录，分析活动，补录缺失积分。

**现有文件**：`cloud_score_sync.py`

**改造后数据流**：

```
xiaozhi.me API
     │
     ▼
cloud_score_sync.py
     │
     ├── 分析聊天内容 → 识别活动
     │       │
     │       ▼
     │   INSERT INTO score_ledger (source='cloud_sync', source_id=chat_id)
     │   ON CONFLICT(date, activity, source_id) DO NOTHING
     │       │
     │       ▼
     │   ✅ 天然防重复: 同个chat_id不会重复计分
     │
     └── 更新 .cloud_sync_log.json（记录已处理的 chat_id）
```

**防重复机制**：
- SQLite 的 `UNIQUE(date, 'english_quiz', chat_id)` 确保同一天的同个聊天不会重复计分
- `.cloud_sync_log.json` 记录已扫描的 chat_id，避免不必要 API 调用

---

## 4. Agent C：兑换商店（消费）

**职责**：管理积分消费（兑换奖励），确保扣分准确。

**改造方案**：

```
reward_shop.py
     │
     ├── 兑换请求
     │       │
     │       ▼
     │   INSERT INTO redemptions (status='pending')
     │   INSERT INTO score_ledger (activity='_redeem', points=-cost, source='redeem')
     │       │
     │       ▼
     │   ✅ 兑换扣分 = score_ledger 中的一条 points=-N 记录
     │      total_score = SUM(score_ledger.points)  # 永远准确！
     │
     └── 家长审批
             │
             ▼
         UPDATE redemptions SET status='approved'
```

**关键原则**：总积分永远从 `SUM(points)` 实时计算，不依赖缓存字段。

---

## 5. 防重复计分总策略

| 层面 | 机制 | 覆盖范围 |
|------|------|---------|
| **数据库层** | `UNIQUE(date, activity, source_id)` | 所有 Agent |
| **同步日志** | chat_id 去重（已同步的不再处理） | Agent B |
| **每日限额** | `SELECT COUNT(*) WHERE date=today AND activity=X` | Agent A |
| **审计** | score_ledger 只追加不修改，历史可追溯 | 全部 |

---

## 6. 迁移方案（零停机）

```
Phase 1: 建库 + 双写
  ┌─────────────┐    ┌──────────────┐
  │ game_data   │    │  SQLite      │
  │ .json (旧)   │◄───┤  (新)        │
  └─────────────┘    └──────────────┘
  读: game_engine.py     读: 新代码
  写: game_engine.py     写: 双写 (JSON + SQLite)

Phase 2: 迁移 + 校验
  - 运行 migration.py: JSON → SQLite
  - 对比 total_score 是否一致
  - 修复不一致的记录

Phase 3: 切换只读 SQLite
  - game_engine.py 改为从 SQLite 读取
  - JSON 仅作为备份/导出

Phase 4: 下线 JSON
  - 确认稳定运行后移除双写逻辑
  - 纯 SQLite 架构
```

---

## 7. 总结对比

```
                  JSON 方案               SQLite 方案
               ──────────────────    ──────────────────
  并发安全         ❌ 需文件锁            ✅ WAL + 事务
  防重复           ❌ 代码层检查           ✅ 数据库约束
  总分准确         ❌ 手动维护             ✅ SUM(points) 实时计算
  查询灵活         ❌ 全量加载过滤          ✅ SQL 查询
  兑换审计         ❌ 不透明               ✅ 独立兑换表
  迁移成本         —                      低（Python 内置 sqlite3）
  学习成本         低                     中（需懂基本 SQL）
```

**建议**：逐步迁移到 SQLite，保持 JSON 双写 3-7 天验证稳定后切换。
