"""
Complete rewrite of game_engine.py - clean version
"""
from pathlib import Path
import json
import os
import sys
from datetime import datetime, date, timedelta
from enum import Enum
import logging

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.WARNING
)
logger = logging.getLogger("xiaozhi_edu")

_LOADED_CONFIG = None
_CONFIG_FILE = None

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    import reward_shop
except ImportError:
    reward_shop = None
DATA_FILE = BASE_DIR / "game_data.json"
DATA_FILE_BACKUP = BASE_DIR / "game_data.json.bak"
POINTS_CONFIG_FILE = BASE_DIR / "points_config.yaml"

CONFIG = None
STREAK_BONUSES = None
DAILY_COMPLETE_BONUS = None
DEFAULT_MULTI_BONUS_THRESHOLDS = None

# === 常量定义 ===

LEARNING_POINTS = {
    "unlock":         {"base": 15, "max_per_day": 3, "label": "Unlock英语"},
    "english_quiz":   {"base": 15, "max_per_day": 2, "label": "英语测验"},
    "math_logic":     {"base": 15, "max_per_day": 3, "label": "数学逻辑"},
    "chinese_recite": {"base": 15, "max_per_day": 2, "label": "国学背书"},
    "speech_practice":{"base": 10, "max_per_day": 1, "label": "口语练习"},
}

CHORE_POINTS = {
    "clean_room":  {"base": 10, "label": "整理房间"},
    "dishes":      {"base": 10, "label": "洗碗"},
    "laundry":     {"base": 10, "label": "洗衣服"},
    "cook":        {"base": 10, "label": "做饭"},
    "sweep":       {"base": 10, "label": "扫地"},
}

POSITIVE_POINTS = {
    "proactive":   {"base": 5,  "label": "主动"},
    "sharing":     {"base": 5,  "label": "分享"},
    "bravery":     {"base": 5,  "label": "勇敢"},
    "help_others": {"base": 5,  "label": "帮助他人"},
}

PENALTY_POINTS = {
    "copying":       {"penalty": 10, "label": "抄写"},
    "breaking_rule": {"penalty": 20, "label": "违反规则"},
}

DAILY_TASKS = {
    "unlock":         {"label": "必做: 英语解锁", "required": True, "optional": False},
    "english_quiz":   {"label": "必做: 英语测验", "required": True, "optional": False},
    "math_logic":     {"label": "必做: 数学逻辑", "required": True, "optional": False},
    "chinese_recite": {"label": "必做: 国学背书", "required": True, "optional": False},
    "speech_practice":{"label": "必做: 口语练习", "required": True, "optional": False},
    "exercise":       {"label": "选做: 运动", "required": False, "optional": True},
    "chore":          {"label": "选做: 家务", "required": False, "optional": True},
    "daily_challenge":{"label": "选做: 每日挑战", "required": False, "optional": True},
}

ACHIEVEMENTS = [
    {"id": "first_unlock", "name": "初次解锁", "desc": "完成首次英语解锁",
     "check": lambda data: any(e.get("activity") == "unlock" for e in data.get("history", []))},
    {"id": "streak_3", "name": "三日连胜", "desc": "连续学习3天",
     "check": lambda data: data.get("streak", {}).get("current", 0) >= 3},
    {"id": "streak_7", "name": "七日连胜", "desc": "连续学习7天",
     "check": lambda data: data.get("streak", {}).get("current", 0) >= 7},
    {"id": "score_100", "name": "百分达人", "desc": "累计达到100分",
     "check": lambda data: data.get("total_score", 0) >= 100},
    {"id": "score_500", "name": "五分大师", "desc": "累计达到500分",
     "check": lambda data: data.get("total_score", 0) >= 500},
]

ACHIEVEMENTS_SPECIAL = [
    {"id": "first_redeem", "name": "首次兑换", "desc": "首次兑换奖励物品",
     "check": lambda data: any(e.get("activity") == "_redeemed_reward" for e in data.get("history", []))},
    {"id": "chore_master", "name": "家务达人", "desc": "完成10次家务",
     "check": lambda data: sum(1 for e in data.get("history", []) if e.get("activity") == "chore") >= 10},
]

LEVEL_THRESHOLDS = [
    (0, "新星"),
    (50, "新星"),
    (150, "小学者"),
    (300, "知识探索家"),
    (500, "学习小明星"),
    (1000, "学习大师"),
]

DEFAULT_DAILY_COMPLETE_BONUS = 30


def set_config_path(path):
    global _CONFIG_FILE, POINTS_CONFIG_FILE
    _CONFIG_FILE = Path(path)
    POINTS_CONFIG_FILE = Path(path)


def _load_points_config() -> dict:
    global _LOADED_CONFIG, CONFIG, STREAK_BONUSES, DAILY_COMPLETE_BONUS, DEFAULT_MULTI_BONUS_THRESHOLDS
    if _LOADED_CONFIG is not None:
        return _LOADED_CONFIG
    _LOADED_CONFIG = _get_default_config()
    if POINTS_CONFIG_FILE.exists():
        try:
            import yaml
            with open(POINTS_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            if cfg and isinstance(cfg, dict):
                _LOADED_CONFIG = cfg
        except Exception:
            pass
    CONFIG = _LOADED_CONFIG
    STREAK_BONUSES = CONFIG.get("streak_bonuses", {3: 5, 7: 10, 14: 15, 30: 20})
    DAILY_COMPLETE_BONUS = CONFIG.get("daily_complete", {}).get("points", DEFAULT_DAILY_COMPLETE_BONUS)
    DEFAULT_MULTI_BONUS_THRESHOLDS = CONFIG.get("multi_bonus_thresholds", {3: 10, 4: 20, 5: 30})
    return _LOADED_CONFIG


def _get_default_config() -> dict:
    return {
        "activities": {
            "unlock": {"points": 15, "daily_limit": 3},
            "english_quiz": {"points": 15, "daily_limit": 2},
            "math_logic": {"points": 15, "daily_limit": 3},
            "chinese_recite": {"points": 15, "daily_limit": 2},
            "speech_practice": {"points": 10, "daily_limit": 1},
            "daily_checkin_morning": {"points": 5, "daily_limit": 1},
            "daily_checkin_afternoon": {"points": 5, "daily_limit": 1},
            "daily_checkin_evening": {"points": 10, "daily_limit": 1},
            "daily_checkin_all": {"points": 15},
            "exercise": {"base_points": 10, "per_10min": 5, "daily_limit": 3},
            "clean_room": {"points": 15},
            "dishes": {"points": 15},
            "laundry": {"points": 15},
            "cook": {"points": 15},
            "sweep": {"points": 15},
            "news_topic": {"points": 0},
            "knowledge": {"points": 0},
            "adventure": {"points": 0},
            "explain": {"points": 0},
            "mickey_f1": {"points": 0},
            "story_song": {"points": 0},
            "praise": {"points": 0},
            "proactive": {"points": 10},
            "copying": {"points": -10},
            "breaking_rule": {"points": -20},
        },
        "streak_bonuses": {3: 5, 7: 10, 14: 15, 30: 20},
        "multi_bonus_thresholds": {3: 10, 4: 20, 5: 30},
        "daily_complete": {
            "points": 30,
            "required_activities": ["unlock", "english_quiz", "math_logic", "chinese_recite", "speech_practice"],
        },
        "penalty_multiplier": {1: 0.8, 2: 0.6, 3: 0.4, 4: 0.2},
        "redemption": {"record_in_history": True, "minimum_score_for_redeem": 0},
    }


def get_activity_points(activity_type: str) -> int:
    act = CONFIG.get("activities", {})
    return act.get(activity_type, {}).get("points", 0)


def get_daily_limit(activity_type: str) -> int:
    act = CONFIG.get("activities", {})
    return act.get(activity_type, {}).get("daily_limit", 999)


def get_streak_bonuses() -> dict:
    return STREAK_BONUSES


def get_multi_bonus_thresholds() -> dict:
    return DEFAULT_MULTI_BONUS_THRESHOLDS


def get_daily_complete_config() -> dict:
    return CONFIG.get("daily_complete", {})


def get_penalty_multiplier(missed_days: int) -> float:
    pm = CONFIG.get("penalty_multiplier", {})
    for days in sorted(pm.keys()):
        if missed_days >= days:
            return pm[days]
    return 1.0


def _load():
    """Load game data from JSON file."""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        logger.warning("Failed to load game data, using empty data")
        return {}


def _save(data):
    """Save game data to JSON file with backup."""
    try:
        if os.path.exists(DATA_FILE):
            import shutil
            shutil.copy2(DATA_FILE, DATA_FILE_BACKUP)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save game data: {e}")


def record_activity(activity_type, points=None, bonus=0, label="",
                    extra=None, streak_type="current"):
    """记录一次活动积分。

    积分计算:
    - points = base_points (从 CONFIG 获取)
    - bonus = streak_bonus (连胜奖励)
    - 每日任务完成奖励 (30分)
    - 多活动类型奖励 (10/20/30分)

    参数:
        activity_type: 活动类型
        points: 基础积分
        bonus: 额外奖励积分
        label: 活动标签
        extra: 额外数据
        streak_type: 连胜类型

    返回:
        记录的实际积分
    """
    if points is None:
        points = get_activity_points(activity_type)

    data = _load()
    today = date.today().isoformat()

    # 断联惩罚
    streak = data.get("streak", {})
    streak_count = streak.get("streak_count", 0)
    streak_dates = streak.get("streak_dates", [])
    if streak_count > 0 and streak_dates:
        last_date = datetime.strptime(streak_dates[-1], "%Y-%m-%d").date()
        missed = (date.today() - last_date).days - 1
        if missed > 0:
            points = int(points * get_penalty_multiplier(missed))

    # 检查多活动类型奖励（penalty 和 praise 不参与 multi_bonus）
    multi_bonus = 0
    if activity_type not in ("penalty", "praise"):
        multi_bonus = _calc_multi_bonus(data, today)
    total_earned = points + bonus + multi_bonus

    # 记录
    entry = {
        "date": today,
        "activity": activity_type,
        "base": points,
        "bonus": bonus,
        "multi_bonus": multi_bonus,
        "total": total_earned,
        "time": datetime.now().isoformat(),
    }
    if label:
        entry["label"] = label
    if extra:
        entry["extra"] = extra

    if "history" not in data:
        data["history"] = []
    data["history"].append(entry)
    data["total_score"] = data.get("total_score", 0) + total_earned

    # 更新连胜
    if streak_type == "current":
        _update_streak(data, today)

    # 检查成就
    data = _check_achievements(data)

    _save(data)
    # 同时写入数据库
    try:
        # 尝试多种路径找到 database 模块
        _db_found = False
        for _db_path in ['/Users/mihua/projects/xiaozhi_admin/backend', os.path.dirname(__file__)]:
            if _db_path not in sys.path:
                sys.path.insert(0, _db_path)
        from database import add_activity
        _db_found = True
        add_activity(
            activity_type=activity_type,
            base=points,
            bonus=bonus,
            multi_bonus=multi_bonus,
            total=total_earned,
            label=label,
            extra=extra,
            date_str=today,
            time_val=entry.get("time", datetime.now().isoformat()),
        )
    except Exception as e:
        print(f"写入数据库失败: {e}")
    return total_earned


def _get_activity_info(activity_type):
    for category in [LEARNING_POINTS, CHORE_POINTS, POSITIVE_POINTS]:
        if activity_type in category:
            return category[activity_type]
    return None


def _count_daily_usage(data, today, activity_type):
    count = 0
    for entry in data.get("history", []):
        if entry.get("date") == today and entry.get("activity") == activity_type:
            count += 1
    return count


def _update_streak(data, today):
    """Update streak tracking.

    逻辑:
    - 如果今天已有记录，不更新连胜
    - 如果昨天有记录，连胜+1
    - 如果昨天没有记录，连胜重置为1

    参数:
        data: 游戏数据
        today: 今日日期字符串
    """
    streak = data.get("streak", {})
    streak_dates = streak.get("streak_dates", [])

    if streak_dates and streak_dates[-1] == today:
        return  # 今天已经记录过

    if streak_dates:
        last_date = datetime.strptime(streak_dates[-1], "%Y-%m-%d").date()
        if (date.today() - last_date).days == 1:
            streak["streak_count"] = streak.get("streak_count", 0) + 1
        else:
            streak["streak_count"] = 1
            streak_dates = []
    else:
        streak["streak_count"] = 1

    streak_dates.append(today)
    streak["streak_dates"] = streak_dates
    data["streak"] = streak


def _calc_multi_bonus(data, today):
    """计算同日多活动类型奖励。

    规则:
    - 3种活动类型: 10分
    - 4种活动类型: 20分
    - 5种活动类型: 30分

    参数:
        data: 游戏数据
        today: 今日日期字符串

    返回:
        奖励积分
    """
    activities_today = set()
    for entry in data.get("history", []):
        if entry.get("date") == today and not entry.get("activity", "").startswith("_"):
            activities_today.add(entry.get("activity"))

    thresholds = DEFAULT_MULTI_BONUS_THRESHOLDS
    bonus = 0
    for threshold, reward in sorted(thresholds.items()):
        if len(activities_today) >= threshold:
            bonus = reward

    if bonus > 0:
        _apply_multi_bonus_marker(data, today, bonus)

    return bonus


def _apply_multi_bonus_marker(data, today, bonus):
    """记录多活动类型奖励标记。

    参数:
        data: 游戏数据
        today: 今日日期字符串
        bonus: 奖励积分
    """
    for entry in data.get("history", []):
        if entry.get("date") == today and entry.get("activity") == "_multi_bonus_applied":
            entry["multi_bonus"] = bonus
            return

    data["history"].append({
        "date": today,
        "activity": "_multi_bonus_applied",
        "base": 0,
        "bonus": 0,
        "multi_bonus": bonus,
        "total": 0,
        "time": datetime.now().isoformat(),
    })


def _get_current_level(total):
    """获取当前等级。

    参数:
        total: 总积分

    返回:
        等级名称
    """
    level = LEVEL_THRESHOLDS[0][1]
    for threshold, name in LEVEL_THRESHOLDS:
        if total >= threshold:
            level = name
    return level


def _check_achievements(data):
    """检查并解锁成就徽章。

    参数:
        data: 游戏数据

    返回:
        更新后的游戏数据
    """
    new = []
    unlocked_achievements = data.get("unlocked_achievements", [])

    for ach in ACHIEVEMENTS:
        if ach["id"] not in unlocked_achievements:
            try:
                if ach["check"](data):
                    unlocked_achievements.append(ach["id"])
                    logger.info(f"Achievement unlocked: {ach['name']}")
            except Exception:
                pass

    data["unlocked_achievements"] = unlocked_achievements

    for ach in ACHIEVEMENTS_SPECIAL:
        if ach["id"] not in unlocked_achievements:
            try:
                if ach["check"](data):
                    unlocked_achievements.append(ach["id"])
                    logger.info(f"Special achievement unlocked: {ach['name']}")
            except Exception:
                pass

    data["unlocked_achievements"] = unlocked_achievements
    return data


def _check_streak_achievement(data, count):
    """检查连胜成就。

    参数:
        data: 游戏数据
        count: 连胜次数

    返回:
        游戏数据（更新后）
    """
    new = []
    unlocked_achievements = data.get("unlocked_achievements", [])

    for ach in ACHIEVEMENTS:
        if ach["id"] not in unlocked_achievements:
            try:
                if ach["check"](data):
                    unlocked_achievements.append(ach["id"])
            except Exception:
                pass

    data["unlocked_achievements"] = unlocked_achievements
    return data


def record_chore(chore_type, label=None):
    """记录家务活动。

    参数:
        chore_type: 家务类型
        label: 活动标签

    返回:
        记录的积分
    """
    info = CHORE_POINTS.get(chore_type, {"base": 10, "label": chore_type})
    points = info.get("base", 10)
    return record_activity("chore", points=points, label=label or info.get("label", chore_type),
                           extra={"chore_type": chore_type})


def record_positive(action_type):
    """记录积极行为。

    参数:
        action_type: 积极行为类型

    返回:
        记录的积分
    """
    info = POSITIVE_POINTS.get(action_type, {"base": 5, "label": action_type})
    points = info.get("base", 5)
    return record_activity("positive", points=points, label=info.get("label", action_type),
                           extra={"action_type": action_type})


def record_penalty(penalty_type, label=None):
    """记录惩罚扣分。

    参数:
        penalty_type: 惩罚类型
        label: 活动标签

    返回:
        扣减的积分（负数）
    """
    info = PENALTY_POINTS.get(penalty_type, {"penalty": 5, "label": penalty_type})
    points = -info.get("penalty", 5)
    return record_activity("penalty", points=points, label=label or info.get("label", penalty_type),
                           extra={"penalty_type": penalty_type})


def get_daily_tasks():
    """获取每日任务状态。"""
    data = _load()
    today = date.today().isoformat()
    tasks = []
    for task_id, task_info in DAILY_TASKS.items():
        done = False
        for entry in data.get("history", []):
            if entry.get("date") == today and entry.get("activity") == task_id:
                done = True
                break
        tasks.append({"id": task_id, **task_info, "completed": done})
    tasks.sort(key=lambda t: (not t["required"], t["id"]))
    return tasks


def redeem_reward(reward_id: str) -> dict:
    """Redeem reward item. Deducts score from total. 优先从数据库查商店配置。"""
    data = _load()
    
    # 优先从数据库查商店配置
    item = None
    try:
        from database import store_config_get_by_id, store_config_get_all
        item = store_config_get_by_id(reward_id)
        if not item:
            all_items = store_config_get_all()
            for r in all_items:
                if r.get("name") == reward_id or r.get("reward_id") == reward_id:
                    item = r
                    break
    except Exception:
        pass
    
    # fallback 到 reward_shop 模块
    if not item and reward_shop:
        shop = reward_shop.get_shop()
        for r in shop:
            if r.get("id") == reward_id or r.get("name") == reward_id:
                item = r
                break
    
    if not item:
        return {"status": "error", "message": f"Reward {reward_id} not found"}
    
    cost = item.get("cost", 0)
    if data.get("total_score", 0) < cost:
        return {"status": "error", "message": f"Insufficient score: {data.get('total_score', 0)} / {cost}"}
    
    # Deduct score
    data["total_score"] -= cost
    
    # Record in history
    today = date.today().isoformat()
    data["history"].append({
        "date": today,
        "activity": "_redeemed_reward",
        "base": -cost,
        "bonus": 0,
        "multi_bonus": 0,
        "total": -cost,
        "time": datetime.now().isoformat(),
        "reward_name": item.get("name", reward_id),
        "cost": cost,
    })
    
    _save(data)
    
    # 写入数据库兑换记录
    try:
        from database import add_redeemed
        add_redeemed(
            reward_id=item.get("reward_id", reward_id),
            reward_name=item.get("name", ""),
            cost=cost,
            date_str=today,
        )
    except Exception as e:
        logger.warning(f"Failed to write redemption to DB: {e}")
    
    # TTS feedback
    tts_text = ""
    try:
        import tts_helper as th
        if hasattr(th, "redeem_tts"):
            tts_text = th.redeem_tts(item.get("name", reward_id), cost)
    except ImportError:
        pass
    
    return {"status": "ok", "remaining_score": data["total_score"],
            "reward_name": item.get("name", reward_id),
            "tts": tts_text,
            "cost": cost,
            "description": item.get("desc", ""),
            "level": _calculate_level(data["total_score"]) if hasattr(ge, "_calculate_level") else _get_level(data["total_score"]),
            "redeemed_rewards": data.get("redeemed_rewards", [])}

def get_score() -> dict:
    """获取完整积分信息。"""
    data = _load()
    total = data.get("total_score", 0)
    level = _get_current_level(total)
    streak = data.get("streak", {})
    history = data.get("history", [])
    unlocked = data.get("unlocked_achievements", [])

    # 计算连胜日期
    streak_dates = streak.get("streak_dates", [])

    # 计算今日收入
    today = date.today().isoformat()
    today_earn = sum(h.get("total", 0) for h in history if h.get("date") == today)

    return {
        "total_score": total,
        "level": level,
        "streak_count": streak.get("streak_count", 0),
        "streak_dates": streak_dates,
        "achievements_unlocked": unlocked,
        "special_achievements": [],
        "today_earnings": today_earn,
        "unlocked_achievements": unlocked,
    }


def get_history(limit: int = 100) -> list:
    """获取近期活动历史。"""
    data = _load()
    history = data.get("history", [])
    return list(history[-limit:])


def get_today_activities() -> dict:
    """获取今日活动分类。"""
    data = _load()
    history = data.get("history", [])
    today = date.today().isoformat()
    today_entries = [h for h in history if h.get("date") == today]

    # 按活动类型分组
    activities = {}
    for entry in today_entries:
        act = entry.get("activity", "unknown")
        if act not in activities:
            activities[act] = {"activity": act, "count": 0, "total_points": 0}
        activities[act]["count"] += 1
        activities[act]["total_points"] += entry.get("total", 0)

    return {
        "date": today,
        "activities": list(activities.values()),
        "total_entries": len(today_entries),
    }


CONFIG = _load_points_config()

if __name__ == "__main__":
    print("game_engine loaded successfully")
