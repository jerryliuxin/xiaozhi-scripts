#!/usr/bin/env python3
"""
migrate.py — 将 game_data.json 迁移到 SQLite

用法: python3 migrate.py [--dry-run]
     --dry-run: 预览迁移内容，不写入数据库
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
JSON_PATH = BASE_DIR / "game_data.json"
DB_PATH = BASE_DIR / "game_data.db"


def migrate_json_to_sqlite(dry_run=False):
    """将 game_data.json 全量迁移到 SQLite。"""
    if not JSON_PATH.exists():
        print(f"❌ 未找到 {JSON_PATH}")
        return False

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    history = data.get('history', [])
    total_score = data.get('total_score', 0)
    streak = data.get('streak', {})
    level = data.get('level', '新星')

    print(f"📋 准备迁移: {len(history)} 条记录, 总分 {total_score}")

    if dry_run:
        print("\n🔍 DRY-RUN 预览:")
        for e in sorted(history, key=lambda x: x.get('date', '')):
            date_str = e.get('date', '?')
            activity = e.get('activity', '?')
            total = e.get('total', e.get('points', 0))
            label = e.get('label', '')
            source = e.get('source', 'legacy')
            print(f"  {date_str} {activity:30s} {total:+4d}  {label[:20]}")
        print(f"\n共 {len(history)} 条")
        return True

    # 导入 database 模块（确保在同一目录）
    sys.path.insert(0, str(BASE_DIR))
    from database import (get_conn, set_global, add_score_entry, 
                          rebuild_total_score, _init_schema)

    conn = get_conn()
    _init_schema(conn)  # 确保表存在

    # 迁移积分流水
    migrated = 0
    skipped = 0
    errors = 0

    for entry in history:
        date_str = entry.get('date', '')
        activity = entry.get('activity', '')
        total = entry.get('total', entry.get('points', 0))
        label = entry.get('label', entry.get('activity', ''))
        source = entry.get('source', 'legacy')
        source_id = entry.get('source_id', f"migrate_{date_str}_{activity}_{migrated}")

        if not date_str or not activity:
            errors += 1
            continue

        result = add_score_entry(
            date_str=date_str,
            activity=activity,
            points=total,
            label=label,
            source=source,
            source_id=source_id,
        )
        if result['ok'] and not result['duplicate']:
            migrated += 1
        elif result['duplicate']:
            skipped += 1
        else:
            errors += 1

    # 迁移全局状态
    set_global('total_score', str(rebuild_total_score()))
    set_global('level', level)
    set_global('streak_count', streak.get('streak_count', 0))
    set_global('streak_dates', json.dumps(streak.get('streak_dates', []), ensure_ascii=False))
    set_global('last_sync_date', datetime.now().isoformat())
    set_global('score_version', '2')

    print(f"\n✅ 迁移完成:")
    print(f"   新增: {migrated} 条")
    print(f"   跳过: {skipped} 条（重复）")
    print(f"   错误: {errors} 条")
    print(f"   总分: {rebuild_total_score()}")
    return True


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    migrate_json_to_sqlite(dry_run=dry_run)
