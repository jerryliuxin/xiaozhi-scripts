"""运动打卡模块 — 跑步/跳绳/球类/游泳等运动追踪


核心功能：
1. 多运动类型（跑步、跳绳、球类、游泳、骑行、其他）
2. 每日运动打卡（每天至少1次运动才有打卡积分）
3. 运动连胜追踪
4. 运动成就体系
5. 运动距离/时长估算积分

设计原则：
- 跑步：每5分钟+5分（上限40分/天），5分钟起算
- 跳绳：每100个+3分（上限30分/天）
- 球类：每次30分（上限2次/天）
- 游泳：每次40分（上限1次/天）
- 骑行：每10分钟+5分（上限30分/天）
- 其他运动：每次15分（上限3次/天）
- 每日运动打卡完成：额外+10分
- 运动连胜里程碑：3/7/14/30天
"""

import json
import os
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "exercise_data.json")

import logging

logger = logging.getLogger("xiaozhi_edu")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)


# --- 运动类型积分配置 ---
EXERCISE_POINTS = {
    "running": {
        "base": 5,
        "unit": "分钟",
        "unit_value": 5,  # 每5分钟5分
        "min_minutes": 5,  # 最少5分钟起算
        "max_per_day": 40,
        "label": "跑步",
    },
    "jump_rope": {
        "base": 3,
        "unit": "个",
        "unit_value": 100,  # 每100个3分
        "max_per_day": 30,
        "label": "跳绳",
    },
    "ball": {
        "base": 30,
        "max_per_day": 60,  # 每次30分，最多2次=60分
        "label": "球类（篮球/足球/羽毛球等）",
    },
    "swimming": {
        "base": 40,
        "max_per_day": 40,  # 每次40分，最多1次
        "label": "游泳",
    },
    "cycling": {
        "base": 5,
        "unit": "分钟",
        "unit_value": 10,  # 每10分钟5分
        "min_minutes": 10,
        "max_per_day": 30,
        "label": "骑行",
    },
    "other": {
        "base": 15,
        "max_per_day": 3,
        "label": "其他运动",
    },
}

# --- 运动连胜奖励 ---
EXERCISE_STREAK_BONUSES = {
    3:  15,
    7:  30,
    14: 50,
    30: 100,
}

# --- 运动成就 ---
EXERCISE_ACHIEVEMENTS = [
    {"total_sessions": 10,  "badge": "🏃", "name": "运动新苗",   "desc": "累计完成10次运动打卡"},
    {"total_sessions": 30,  "badge": "🏃‍♂️", "name": "运动达人",   "desc": "累计完成30次运动打卡"},
    {"total_sessions": 100, "badge": "🏅", "name": "运动健将",   "desc": "累计完成100次运动打卡"},
    {"total_minutes": 300,  "badge": "🏃‍♀️", "name": "千里之行",   "desc": "累计运动300分钟"},
    {"total_minutes": 1000, "badge": "🥇", "name": "运动之王",   "desc": "累计运动1000分钟"},
    {"streak": 30,          "badge": "🔥", "name": "运动连胜30天", "desc": "连续运动30天"},
]

# 运动类型默认时长估算（分钟）
EXERCISE_DEFAULT_MINUTES = {
    "running": 15,
    "jump_rope": 5,
    "ball": 45,
    "swimming": 30,
    "cycling": 20,
    "other": 15,
}


def _default_duration(exercise_type):
    """按运动类型返回合理默认时长。"""
    return EXERCISE_DEFAULT_MINUTES.get(exercise_type, 10)


def _load():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {
        "history": [],
        "exercise_streak": 0,
        "exercise_streak_dates": [],
        "last_exercise_date": None,
        "total_sessions": 0,
        "total_minutes": 0,
        "exercise_achievements_unlocked": [],
        "daily_checkin_completed": False,
        # 运动类型次数统计
        "running_count": 0,
        "jump_rope_count": 0,
        "ball_count": 0,
        "swimming_count": 0,
        "cycling_count": 0,
        "other_count": 0,
    }


def _save(data):
    """保存数据（原子写入）。"""
    try:
        tmp_file = DATA_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, DATA_FILE)
        return True
    except Exception:
        return False


def record_exercise(exercise_type, duration_minutes=0, count=0, label=None):
    """
    记录一次运动。
    
    exercise_type: 运动类型（running/jump_rope/ball/swimming/cycling/other）
    duration_minutes: 运动时长（分钟），用于跑步/骑行
    count: 数量，用于跳绳（个数）
    label: 自定义标签
    """
    info = EXERCISE_POINTS.get(exercise_type, EXERCISE_POINTS["other"])
    if label is None:
        label = info["label"]
    
    data = _load()
    today = date.today().isoformat()
    
    # 1. 计算本次运动获得的积分
    earned_points = _calc_exercise_points(data, today, exercise_type, duration_minutes, count, info)
    if isinstance(earned_points, dict) and "error" in earned_points:
        return earned_points
    
    # 2. 检查运动连胜
    new_streak, streak_bonus = _calc_exercise_streak(data, today)
    
    # 3. 更新统计数据
    data["total_sessions"] += 1
    data["total_minutes"] += duration_minutes if duration_minutes > 0 else _default_duration(exercise_type)
    
    # 更新各类型计数
    type_key = exercise_type + "_count"
    if type_key in data:
        data[type_key] += 1
    
    # 4. 同时记录到主积分系统（game_engine），同步到总积分
    #    运动积分也计入 total_score，并触发连胜检查
    import game_engine as ge

    main_result = ge.record_activity(
        f"exercise_{exercise_type}",
        points=0,  # 运动积分单独计算，不通过主系统
        bonus=earned_points + streak_bonus,
        label=f"运动-{info['label']}"
    )
    
    # 5. 记录到本地数据
    entry = {
        "date": today,
        "exercise": exercise_type,
        "label": label,
        "duration_minutes": duration_minutes,
        "count": count,
        "earned_points": earned_points,
        "streak_bonus": streak_bonus,
        "total": earned_points + streak_bonus,
    }
    data["history"].append(entry)
    
    # 清理旧记录（保留最近90天）
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    data["history"] = [e for e in data["history"] if e.get("date", "") >= cutoff]
    
    _save(data)
    
    # 6. 检查运动成就
    new_achievements = _check_exercise_achievements(data)
    
    # 7. 检查每日打卡是否完成
    today_exercises = [e for e in data["history"] if e.get("date") == today]
    if today_exercises and not data.get("daily_checkin_completed", False):
        data["daily_checkin_completed"] = True
    
    return {
        "exercise": exercise_type,
        "label": label,
        "duration_minutes": duration_minutes,
        "count": count,
        "earned_points": earned_points,
        "streak_bonus": streak_bonus,
        "total": earned_points + streak_bonus,
        "streak_count": new_streak,
        "total_sessions": data["total_sessions"],
        "total_minutes": data["total_minutes"],
        "new_achievements": new_achievements,
        "checkin_completed": data.get("daily_checkin_completed", False),
    }


def _calc_exercise_points(data, today, exercise_type, duration_minutes, count, info):
    """计算单次运动获得的积分。"""
    today_type_entries = [
        e for e in data.get("history", [])
        if e.get("date") == today and e.get("exercise") == exercise_type
    ]
    today_type_points = sum(e.get("earned_points", 0) for e in today_type_entries)
    
    max_per_day = info.get("max_per_day", 99)
    if today_type_points >= max_per_day:
        return {"error": f"{info['label']} 今日已达上限（{max_per_day}分）"}
    
    earned = 0
    
    if exercise_type == "running":
        # 跑步：每5分钟5分，5分钟起算
        if duration_minutes < 5:
            return {"error": "跑步最少需要5分钟才能计分"}
        earned = (duration_minutes // 5) * 5
    elif exercise_type == "jump_rope":
        # 跳绳：每100个3分
        if count < 1:
            count = 100  # 默认100个
        earned = (count // 100) * 3
    elif exercise_type == "ball":
        # 球类：每次30分
        earned = 30
    elif exercise_type == "swimming":
        # 游泳：每次40分
        earned = 40
    elif exercise_type == "cycling":
        # 骑行：每10分钟5分
        if duration_minutes < 10:
            return {"error": "骑行最少需要10分钟才能计分"}
        earned = (duration_minutes // 10) * 5
    elif exercise_type == "other":
        # 其他：每次15分
        earned = 15
    
    # 检查是否超过日上限
    if today_type_points + earned > max_per_day:
        earned = max_per_day - today_type_points
    
    return earned


def _calc_exercise_streak(data, today):
    """计算运动连胜。"""
    last = data.get("last_exercise_date")
    streak_dates = data.get("exercise_streak_dates", [])
    
    if last is None:
        data["exercise_streak"] = 1
        data["exercise_streak_dates"] = [today]
        return 1, 0
    
    last_date = datetime.strptime(last, "%Y-%m-%d").date()
    today_date = datetime.strptime(today, "%Y-%m-%d").date()
    delta = (today_date - last_date).days
    
    if delta == 0:
        # 同一天不增加连胜，但更新 last_exercise_date
        if today not in streak_dates:
            streak_dates.append(today)
        data["last_exercise_date"] = today
    elif delta == 1:
        # 前一天 — 继续连胜
        if today not in streak_dates:
            streak_dates.append(today)
        data["exercise_streak"] = len(streak_dates)
        data["last_exercise_date"] = today  # 补充保存
        
        # 检查连胜里程碑
        bonus = 0
        for milestone, b in sorted(EXERCISE_STREAK_BONUSES.items()):
            if data["exercise_streak"] >= milestone:
                bonus = b
        
        return data["exercise_streak"], bonus
    else:
        # 断联
        missed_days = delta - 1
        if missed_days >= 3:
            # 断联3天以上重置连胜
            data["exercise_streak"] = 0
            streak_dates = []
        elif missed_days == 1:
            # 断联1天不重置，但也不增加
            pass
        
        data["exercise_streak"] = 1
        streak_dates = [today]
    
    data["exercise_streak_dates"] = streak_dates
    data["last_exercise_date"] = today
    return data["exercise_streak"], 0


def _check_exercise_achievements(data):
    """检查运动成就。"""
    new = []
    unlocked_names = set(
        e.get("name") for e in data.get("exercise_achievements_unlocked", [])
    )
    
    for ach in EXERCISE_ACHIEVEMENTS:
        if ach["name"] in unlocked_names:
            continue
        
        earned = False
        if ach.get("total_sessions") and data.get("total_sessions", 0) >= ach["total_sessions"]:
            earned = True
        elif ach.get("total_minutes") and data.get("total_minutes", 0) >= ach["total_minutes"]:
            earned = True
        elif ach.get("streak") and data.get("exercise_streak", 0) >= ach["streak"]:
            earned = True
        
        if earned:
            new.append(ach)
            data.setdefault("exercise_achievements_unlocked", []).append({
                "name": ach["name"],
                "badge": ach["badge"],
                "desc": ach["desc"],
            })
    
    if new:
        _save(data)
    return new


def get_daily_exercise_status():
    """获取今日运动状态和打卡信息。"""
    data = _load()
    today = date.today().isoformat()
    today_entries = [e for e in data.get("history", []) if e.get("date") == today]
    
    today_total_points = sum(e.get("total", 0) for e in today_entries)
    today_minutes = sum(e.get("duration_minutes", 0) for e in today_entries) or (len(today_entries) * 10)
    
    # 检查打卡完成
    checkin_done = len(today_entries) >= 1
    
    # 今日运动类型分布
    types_today = {}
    for e in today_entries:
        t = e.get("exercise", "unknown")
        if t not in types_today:
            types_today[t] = {"count": 0, "minutes": 0}
        types_today[t]["count"] += 1
        types_today[t]["minutes"] += e.get("duration_minutes", 0)
    
    # 下次运动类型推荐
    recommended = _get_exercise_recommendation(data, today_entries)
    
    return {
        "date": today,
        "checkin_completed": checkin_done,
        "exercise_count": len(today_entries),
        "total_points": today_total_points,
        "total_minutes": today_minutes,
        "types": types_today,
        "streak": data.get("exercise_streak", 0),
        "next_streak_milestone": _get_next_streak_milestone(data.get("exercise_streak", 0)),
        "recommended": recommended,
    }


def _get_exercise_recommendation(data, today_entries):
    """根据今日运动情况推荐下次运动。"""
    if not today_entries:
        return "还没运动呢！先从跑步开始吧，5分钟就有积分了！🏃"
    
    types_done = set(e.get("exercise") for e in today_entries)
    
    if "running" not in types_done:
        return "试试跑步吧！每5分钟+5分，跑步锻炼心肺功能！"
    if "jump_rope" not in types_done:
        return "来跳个绳吧！每100个+3分，跳绳还能长高哦！"
    if "ball" not in types_done:
        return "打场球吧！篮球/足球/羽毛球都可以，每次30分！"
    
    return "今天运动很全面了！再多做点拉伸放松吧 🧘"


def _get_next_streak_milestone(current_streak):
    """获取下一个运动连胜里程碑。"""
    for milestone, bonus in sorted(EXERCISE_STREAK_BONUSES.items()):
        if current_streak < milestone:
            return {"days": milestone, "bonus": bonus}
    return None


def get_exercise_achievements():
    """获取运动成就列表和当前进度。"""
    data = _load()
    unlocked = set(e.get("name") for e in data.get("exercise_achievements_unlocked", []))
    result = []
    
    for ach in EXERCISE_ACHIEVEMENTS:
        done = ach["name"] in unlocked
        progress = ""
        
        if ach.get("total_sessions"):
            done_count = data.get("total_sessions", 0)
            progress = f"{done_count}/{ach['total_sessions']}次"
        elif ach.get("total_minutes"):
            done_count = data.get("total_minutes", 0)
            progress = f"{done_count}/{ach['total_minutes']}分钟"
        elif ach.get("streak"):
            done_count = data.get("exercise_streak", 0)
            progress = f"{done_count}/{ach['streak']}天"
        
        result.append({
            "badge": ach["badge"],
            "name": ach["name"],
            "desc": ach["desc"],
            "unlocked": done,
            "progress": progress,
        })
    
    return result


def get_exercise_history(limit=10):
    """获取运动历史记录。"""
    data = _load()
    return list(reversed(data.get("history", [])[-limit:]))


if __name__ == "__main__":
    # 测试
    print("=== 运动打卡模块测试 ===")
    
    # 记录跑步15分钟
    r1 = record_exercise("running", duration_minutes=15)
    print(f"跑步15分钟: {json.dumps(r1, ensure_ascii=False)}")
    
    # 记录跳绳200个
    r2 = record_exercise("jump_rope", count=200)
    print(f"跳绳200个: {json.dumps(r2, ensure_ascii=False)}")
    
    # 查看状态
    status = get_daily_exercise_status()
    print(f"今日状态: {json.dumps(status, ensure_ascii=False)}")
    
    # 查看成就
    achievements = get_exercise_achievements()
    print(f"成就: {json.dumps(achievements, ensure_ascii=False)}")
