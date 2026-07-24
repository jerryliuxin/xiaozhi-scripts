#!/usr/bin/env python3
"""
database.py — SQLite 积分核心存储层

设计原则：
1. SQLite WAL 模式，支持多进程并发读写
2. score_ledger 只追加不修改，全量可审计
3. 总积分 = SUM(points)，杜绝手动维护偏差
4. UNIQUE 约束防止重复计分
5. JSON 双写（过渡期，3-7天后可关闭）
"""

import sqlite3
import json
import os
import threading
import sys
from datetime import date, datetime
from pathlib import Path

# Python 3.9 sqlite3 import 深度较深，增加递归上限避免偶尔 RecursionError
if sys.getrecursionlimit() < 10000:
    sys.setrecursionlimit(10000)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "game_data.db"
GAME_DATA_JSON = BASE_DIR / "game_data.json"

# 线程本地连接，避免多线程共享连接
_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """获取当前线程的数据库连接（自动创建）。"""
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = _create_conn()
    return _local.conn


def _create_conn() -> sqlite3.Connection:
    """创建新连接并初始化 WAL 模式。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn):
    """初始化数据库表结构。"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS score_ledger (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    NOT NULL,
            activity    TEXT    NOT NULL,
            points      INTEGER NOT NULL DEFAULT 0,
            label       TEXT    DEFAULT '',
            source      TEXT    NOT NULL DEFAULT 'voice',
            source_id   TEXT    DEFAULT '',
            chat_id     TEXT    DEFAULT NULL,
            extra       TEXT    DEFAULT '{}',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            UNIQUE(date, activity, source, source_id)
        );

        CREATE INDEX IF NOT EXISTS idx_ledger_date ON score_ledger(date);
        CREATE INDEX IF NOT EXISTS idx_ledger_activity ON score_ledger(activity);
        CREATE INDEX IF NOT EXISTS idx_ledger_source ON score_ledger(source);

        CREATE TABLE IF NOT EXISTS redemptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            reward_id   TEXT    NOT NULL,
            reward_name TEXT    NOT NULL,
            cost        INTEGER NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'pending',
            requested_at TEXT   NOT NULL DEFAULT (datetime('now', 'localtime')),
            approved_at TEXT,
            approved_by TEXT    DEFAULT '',
            note        TEXT    DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS global_state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        -- 插入默认值（如不存在）
        INSERT OR IGNORE INTO global_state (key, value) VALUES ('total_score', '0');
        INSERT OR IGNORE INTO global_state (key, value) VALUES ('level', '新星');
        INSERT OR IGNORE INTO global_state (key, value) VALUES ('streak_count', '0');
        INSERT OR IGNORE INTO global_state (key, value) VALUES ('streak_dates', '[]');
        INSERT OR IGNORE INTO global_state (key, value) VALUES ('last_sync_date', '');
        INSERT OR IGNORE INTO global_state (key, value) VALUES ('score_version', '2');
    """)
    conn.commit()


# ═══════════════════════════════════════════════════
#  写入操作（事务保护）
# ═══════════════════════════════════════════════════

def add_score_entry(date_str: str, activity: str, points: int, *,
                    label: str = '', source: str = 'voice', source_id: str = '',
                    chat_id: str = None, extra: dict = None, time_str: str = None) -> dict:
    """添加一条积分流水（事务保护）。

    返回 {'ok': bool, 'id': int|None, 'points': int, 'duplicate': bool}
    """
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if time_str:
            cursor = conn.execute("""
                INSERT INTO score_ledger (date, activity, points, label, source, source_id, chat_id, extra, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_str, activity, points, label, source, source_id, chat_id, 
                  json.dumps(extra or {}, ensure_ascii=False),
                  f"{date_str} {time_str}"))
        else:
            cursor = conn.execute("""
                INSERT INTO score_ledger (date, activity, points, label, source, source_id, chat_id, extra)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_str, activity, points, label, source, source_id, chat_id, 
                  json.dumps(extra or {}, ensure_ascii=False)))
        entry_id = cursor.lastrowid

        # 更新 total_score
        conn.execute("""
            UPDATE global_state SET value = CAST(
                CAST((SELECT value FROM global_state WHERE key = 'total_score') AS INTEGER) + ? AS TEXT
            ) WHERE key = 'total_score'
        """, (points,))

        conn.commit()

        return {'ok': True, 'id': entry_id, 'points': points, 'duplicate': False}

    except sqlite3.IntegrityError:
        conn.rollback()
        return {'ok': True, 'id': None, 'points': 0, 'duplicate': True}

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"写入积分失败: {e}") from e


def add_redemption(reward_id: str, reward_name: str, cost: int) -> dict:
    """创建兑换请求（同时扣分）。"""
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")

        # 验证积分足够
        row = conn.execute("SELECT value FROM global_state WHERE key = 'total_score'").fetchone()
        current_score = int(row['value'])
        if current_score < cost:
            conn.rollback()
            return {'ok': False, 'error': f'积分不足，需要 {cost}，当前 {current_score}'}

        # 创建兑换记录
        conn.execute("""
            INSERT INTO redemptions (reward_id, reward_name, cost)
            VALUES (?, ?, ?)
        """, (reward_id, reward_name, cost))

        # 扣分（记一条负分流水）
        source_id = f"redeem_{reward_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        conn.execute("""
            INSERT INTO score_ledger (date, activity, points, label, source, source_id)
            VALUES (?, '_redeem', ?, ?, 'redeem', ?)
        """, (date.today().isoformat(), -cost, f"兑换: {reward_name}", source_id))

        # 更新 total_score
        conn.execute("""
            UPDATE global_state SET value = CAST(
                CAST((SELECT value FROM global_state WHERE key = 'total_score') AS INTEGER) + ? AS TEXT
            ) WHERE key = 'total_score'
        """, (-cost,))

        conn.commit()
        return {'ok': True, 'cost': cost}

    except sqlite3.IntegrityError:
        conn.rollback()
        return {'ok': False, 'error': '重复兑换请求'}

    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}


# ═══════════════════════════════════════════════════
#  读取操作
# ═══════════════════════════════════════════════════

def get_total_score() -> int:
    """获取总积分。"""
    row = get_conn().execute("SELECT value FROM global_state WHERE key = 'total_score'").fetchone()
    return int(row['value']) if row else 0


def get_global(key: str, default=None):
    """读取全局状态。"""
    row = get_conn().execute("SELECT value FROM global_state WHERE key = ?", (key,)).fetchone()
    if row:
        try:
            return json.loads(row['value'])
        except (json.JSONDecodeError, TypeError):
            return row['value']
    return default


def set_global(key: str, value):
    """写入全局状态。"""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    else:
        value = str(value)
    conn = get_conn()
    conn.execute("""
        INSERT INTO global_state (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()


def get_history(date_from: str = None, date_to: str = None,
                activity: str = None, source: str = None,
                limit: int = 1000, offset: int = 0) -> list:
    """查询积分流水。"""
    where = []
    params = []
    if date_from:
        where.append("date >= ?"); params.append(date_from)
    if date_to:
        where.append("date <= ?"); params.append(date_to)
    if activity:
        where.append("activity = ?"); params.append(activity)
    if source:
        where.append("source = ?"); params.append(source)

    sql = "SELECT * FROM score_ledger"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC"
    sql += f" LIMIT {limit} OFFSET {offset}"

    rows = get_conn().execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_daily_count(date_str: str, activity: str) -> int:
    """查询某天某活动的记录数（用于每日限额检查）。"""
    row = get_conn().execute("""
        SELECT COUNT(*) as cnt FROM score_ledger
        WHERE date = ? AND activity = ?
    """, (date_str, activity)).fetchone()
    return row['cnt']


def get_daily_activities(date_str: str) -> set:
    """查询某天有哪些活动类型（用于 multi_bonus 计算）。"""
    rows = get_conn().execute("""
        SELECT DISTINCT activity FROM score_ledger
        WHERE date = ? AND activity NOT IN ('praise', 'penalty', '_redeem', '_multi_bonus_applied')
          AND activity NOT LIKE '\_%'
    """, (date_str,)).fetchall()
    return {r['activity'] for r in rows}


# ═══════════════════════════════════════════════════
#  JSON 双写（过渡期用，保持向前兼容）
# ═══════════════════════════════════════════════════

def close():
    """关闭当前线程的连接。"""
    if hasattr(_local, 'conn') and _local.conn:
        _local.conn.close()
        _local.conn = None


def rebuild_total_score():
    """校验并重建 total_score（从流水重新加总）。"""
    conn = get_conn()
    row = conn.execute("SELECT COALESCE(SUM(points), 0) as total FROM score_ledger").fetchone()
    actual = row['total']
    conn.execute("UPDATE global_state SET value = ? WHERE key = 'total_score'", (str(actual),))
    conn.commit()
    return actual


if __name__ == '__main__':
    import sys
    if '--rebuild' in sys.argv:
        total = rebuild_total_score()
        print(f"✅ 总分已重建: {total}")
    elif '--migrate' in sys.argv:
        from migrate import migrate_json_to_sqlite
        migrate_json_to_sqlite()
    elif '--check' in sys.argv:
        total = get_total_score()
        count = len(get_history())
        print(f"💰 总积分: {total}")
        print(f"📋 总流水: {count} 条")
        print(f"📦 数据库: {DB_PATH}")
