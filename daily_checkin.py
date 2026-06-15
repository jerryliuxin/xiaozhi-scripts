"""每日打卡提醒系统 — 促进米奇每天坚持学习和运动


import logging

logger = logging.getLogger("xiaozhi_edu")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)

核心功能：
1. 每日打卡检查（学习+运动）
2. 打卡状态追踪（早中晚三次打卡）
3. 打卡奖励（早打卡+5, 中打卡+5, 晚打卡+10+每日总结）
4. 连续打卡成就
5. 智能提醒（根据时段推送不同内容）
6. 打卡缺失惩罚（断联时温和提醒，不是批评）

打卡机制：
- 早打卡（6:00-12:00）：完成今日第一个学习活动 +5分
- 中打卡（12:00-18:00）：完成运动或下午学习 +5分
- 晚打卡（18:00-24:00）：完成晚间学习/回顾 +10分 + 每日总结
- 每日全打卡：额外+15分
"""

import json
import os
import sys
from datetime import datetime, date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_engine
import logging

# === logging 配置 ===
logger = logging.getLogger("xiaozhi_edu")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "checkin_data.json")

# --- 时段定义 ---
TIME_PERIODS = {
    "morning":  {"start": 6,  "end": 12,  "label": "早上", "bonus": 5},
    "afternoon": {"start": 12, "end": 18, "label": "中午", "bonus": 5},
    "evening":   {"start": 18, "end": 24, "label": "晚上", "bonus": 10},
}

# --- 连续打卡奖励 ---
CHECKIN_STREAK_BONUSES = {
    3:   10,
    7:   20,
    14:  30,
    30:  60,
    60:  100,
    100: 200,
}

# --- 打卡成就 ---
CHECKIN_ACHIEVEMENTS = [
    {"streak": 7,   "badge": "📅", "name": "一周打卡",   "desc": "连续打卡7天"},
    {"streak": 30,  "badge": "🏅", "name": "月度达人",   "desc": "连续打卡30天"},
    {"streak": 100, "badge": "🏆", "name": "百日冲刺",   "desc": "连续打卡100天"},
]


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
        "checkin_history": [],
        "checkin_streak": 0,
        "checkin_streak_dates": [],
        "last_checkin_date": None,
        "achievements_unlocked": [],
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


def _get_current_period():
    """获取当前时段。"""
    hour = datetime.now().hour
    for period_id, period in TIME_PERIODS.items():
        if period["start"] <= hour < period["end"]:
            return period_id, period
    # 0-5点不算打卡时间
    return None, None


def checkin(period_id=None):
    """
    执行打卡。
    
    period_id: 时段（morning/afternoon/evening），自动检测当前时段
    返回打卡结果和今日状态。
    """
    data = _load()
    today = date.today().isoformat()
    now = datetime.now()
    
    # 自动检测时段
    if period_id is None:
        period_id, period = _get_current_period()
        if period is None:
            return {
                "error": "现在不是打卡时间（6:00-24:00）。明天早上6点后记得打卡哦！",
                "current_hour": now.hour,
            }
    else:
        period = TIME_PERIODS.get(period_id)
        if period is None:
            return {"error": "无效的时段，可用：morning/afternoon/evening"}
    
    # 检查今天是否已打过这个时段的卡
    today_checkins = [
        e for e in data.get("checkin_history", [])
        if e.get("date") == today and e.get("period") == period_id
    ]
    
    if today_checkins:
        return {
            "error": f"{period['label']}已经打过卡了！今天打了 {len(today_checkins)} 次卡。",
            "date": today,
            "period": period_id,
            "today_checkin_count": len(today_checkins),
        }
    
    # 记录打卡
    entry = {
        "date": today,
        "period": period_id,
        "period_label": period["label"],
        "bonus": period["bonus"],
        "time": now.strftime("%H:%M:%S"),
    }
    data.setdefault("checkin_history", []).append(entry)
    
    # 清理旧记录（保留90天）
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    data["checkin_history"] = [
        e for e in data["checkin_history"]
        if e.get("date", "") >= cutoff
    ]
    
    # 计算连续打卡
    new_streak, streak_bonus = _calc_checkin_streak(data, today)
    
    # 每日全打卡检测
    today_all = [
        e for e in data["checkin_history"]
        if e.get("date") == today
    ]
    all_done = len(today_all) >= 3
    if all_done and not data.get("daily_all_claimed", False):
        data["daily_all_claimed"] = True
        daily_all_bonus = 15
    else:
        daily_all_bonus = 0
        all_done = False
    
    total_bonus = period["bonus"] + streak_bonus + daily_all_bonus
    
    _save(data)
    
    # 同步记录到主积分系统（game_engine）
    checkin_activity_map = {
        "morning": ("daily_checkin_morning", period["bonus"], "早打卡"),
        "afternoon": ("daily_checkin_afternoon", period["bonus"], "午打卡"),
        "evening": ("daily_checkin_evening", period["bonus"], "晚打卡"),
    }
    activity_type, checkin_bonus, label = checkin_activity_map.get(period_id, ("daily_checkin", period["bonus"], "打卡"))
    ge_result = game_engine.record_activity(activity_type, points=checkin_bonus, bonus=streak_bonus + daily_all_bonus, label=label)
    ge_error = ge_result.get("error", "") if isinstance(ge_result, dict) else ""
    
    # 构建回复
    msg = f"✅ 打卡成功！{period['label']}打卡 (+{period['bonus']}分)\n"
    msg += f"⏰ 时间：{entry['time']}\n"
    
    if streak_bonus > 0:
        msg += f"🔥 连续打卡 {new_streak} 天，连胜奖励 +{streak_bonus}分！\n"
    
    if daily_all_bonus > 0:
        msg += f"🎉 今日三次打卡全部完成！额外奖励 +{daily_all_bonus}分！\n"
    
    msg += f"💰 今日打卡总奖励：+{total_bonus}分\n"
    
    # 剩余打卡
    remaining = 3 - len(today_all)
    if remaining > 0:
        msg += f"📋 今日还需打卡 {remaining} 次"
    
    return {
        "success": True,
        "message": msg,
        "date": today,
        "period": period_id,
        "period_label": period["label"],
        "bonus": period["bonus"],
        "streak_bonus": streak_bonus,
        "daily_all_bonus": daily_all_bonus,
        "total_bonus": total_bonus,
        "streak_count": new_streak,
        "today_checkin_count": len(today_all),
        "all_done": all_done,
        "remaining": remaining,
        "game_engine_recorded": ge_result if isinstance(ge_result, dict) else {},
    }


def _calc_checkin_streak(data, today):
    """计算连续打卡天数。"""
    last = data.get("last_checkin_date")
    streak_dates = data.get("checkin_streak_dates", [])
    
    if last is None:
        data["checkin_streak"] = 1
        data["checkin_streak_dates"] = [today]
        return 1, 0
    
    last_date = datetime.strptime(last, "%Y-%m-%d").date()
    today_date = datetime.strptime(today, "%Y-%m-%d").date()
    delta = (today_date - last_date).days
    
    if delta == 0:
        # 同一天多次打卡不增加连续天数
        return data["checkin_streak"], 0
    elif delta == 1:
        # 连续 — 只在第一天加日期
        if today not in streak_dates:
            streak_dates.append(today)
        data["checkin_streak"] = len(streak_dates)
        
        # 检查里程碑奖励
        bonus = 0
        for milestone, b in sorted(CHECKIN_STREAK_BONUSES.items()):
            if data["checkin_streak"] >= milestone:
                bonus = b
        
        # 检查成就
        _check_checkin_achievements(data, data["checkin_streak"])
        
        return data["checkin_streak"], bonus
    else:
        # 断联 — 重置
        data["checkin_streak"] = 1
        streak_dates = [today]
    
    data["checkin_streak_dates"] = streak_dates
    data["last_checkin_date"] = today
    return data["checkin_streak"], 0


def _check_checkin_achievements(data, count):
    """检查打卡成就。"""
    for ach in CHECKIN_ACHIEVEMENTS:
        if ach.get("streak") and count >= ach["streak"]:
            unlocked_names = set(
                e.get("name") for e in data.get("achievements_unlocked", [])
            )
            if ach["name"] not in unlocked_names:
                data.setdefault("achievements_unlocked", []).append({
                    "name": ach["name"],
                    "badge": ach["badge"],
                    "desc": ach["desc"],
                })
    _save(data)


def get_checkin_status():
    """获取今日打卡状态。"""
    data = _load()
    today = date.today().isoformat()
    now = datetime.now()
    
    today_checkins = [
        e for e in data.get("checkin_history", [])
        if e.get("date") == today
    ]
    
    # 判断当前时段
    current_period, current_period_info = _get_current_period()
    
    # 已完成和待完成
    completed_periods = [e.get("period") for e in today_checkins]
    pending_periods = []
    for pid, pinfo in TIME_PERIODS.items():
        if pid not in completed_periods:
            # 只显示还没过去的时段
            if current_period is not None and pinfo["start"] <= now.hour:
                pending_periods.append({
                    "id": pid,
                    "label": pinfo["label"],
                    "bonus": pinfo["bonus"],
                    "time_range": f"{pinfo['start']}:00-{pinfo['end']}:00",
                })
    
    # 打卡总奖励
    today_total = sum(e.get("bonus", 0) for e in today_checkins)
    
    # 连续打卡状态
    streak = data.get("checkin_streak", 0)
    next_milestone = None
    for m, b in sorted(CHECKIN_STREAK_BONUSES.items()):
        if streak < m:
            next_milestone = {"days": m, "bonus": b}
            break
    
    # 生成儿童友好的打卡状态消息
    status_text = f"📅 今日打卡状态\n"
    status_text += f"━━━━━━━━━━━━━━━━━━━\n"
    status_text += f"💰 今日打卡积分：{today_total}分\n"
    status_text += f"📊 已打卡 {len(today_checkins)}/3 次\n"
    status_text += f"🔥 连续打卡：{streak}天\n\n"
    
    # 已完成
    for e in today_checkins:
        status_text += f"✅ {e['period_label']} ({e['time']}) +{e['bonus']}分\n"
    
    # 待完成
    if pending_periods:
        status_text += f"\n📋 待打卡：\n"
        for p in pending_periods:
            status_text += f"  {p['label']} ({p['time_range']}，+{p['bonus']}分)\n"
    else:
        if len(today_checkins) == 3:
            status_text += f"\n🎉 今日三次打卡全部完成！太棒了！\n"
        else:
            status_text += f"\n💡 现在不是打卡时间，明天再来吧！\n"
    
    # 连胜里程碑
    if next_milestone:
        status_text += f"\n🏅 下次连胜奖励：连续{next_milestone['days']}天可拿{next_milestone['bonus']}分！\n"
    
    return {
        "date": today,
        "checkin_count": len(today_checkins),
        "max_checkins": 3,
        "today_points": today_total,
        "streak": streak,
        "completed_periods": completed_periods,
        "pending_periods": pending_periods,
        "next_milestone": next_milestone,
        "status_text": status_text,
    }


def get_checkin_reminder():
    """
    生成智能打卡提醒，根据当前时段和昨日完成情况。
    用于教育客户端的推送。
    """
    data = _load()
    current_period, period_info = _get_current_period()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    # 查找昨天的打卡数据
    yesterday_checkins = [
        e for e in data.get("checkin_history", [])
        if e.get("date") == yesterday
    ]
    yesterday_done = len(yesterday_checkins)
    
    msg = ""
    
    if current_period is None:
        msg = "⏰ 小提醒：明天早上6点后记得来打卡哦！连续打卡有额外奖励！"
    elif current_period == "morning":
        if yesterday_done < 3:
            msg = (
                f"☀️ 早上好，米奇！该来打卡啦！\n"
                f"昨天打了 {yesterday_done}/3 次卡，\n"
                f"今天来个完美的早晨打卡吧！+5分哦！🏃"
            )
        else:
            msg = (
                f"☀️ 早上好，米奇！你是全勤小明星！\n"
                f"继续打卡保持连胜吧！+5分！💪"
            )
    elif current_period == "afternoon":
        today_checkins = [
            e for e in data.get("checkin_history", [])
            if e.get("date") == today
        ]
        if len(today_checkins) == 0:
            msg = (
                f"🌤 中午好！还没打卡吧？\n"
                f"运动一下，然后打卡！+5分！\n"
                f"🏀 篮球/⚽️足球/🏃跑步都行！"
            )
        else:
            msg = (
                f"🌤 下午打卡时间到！\n"
                f"今天已经打1次卡了，再加一次就满3次！+5分！"
            )
    elif current_period == "evening":
        today_checkins = [
            e for e in data.get("checkin_history", [])
            if e.get("date") == today
        ]
        if len(today_checkins) < 3:
            msg = (
                f"🌙 晚上好！今日最后一个打卡窗口！\n"
                f"完成晚间打卡 +10分 + 每日全打卡 +15分！\n"
                f"总结一下今天学了什么吧 📖"
            )
        else:
            msg = (
                f"🌙 太棒了！今日三次打卡全部完成！\n"
                f"今天辛苦了，明天继续打卡！🎉"
            )
    
    return msg


def get_checkin_achievements():
    """获取打卡成就列表。"""
    data = _load()
    unlocked = set(
        e.get("name") for e in data.get("achievements_unlocked", [])
    )
    result = []
    streak = data.get("checkin_streak", 0)
    
    for ach in CHECKIN_ACHIEVEMENTS:
        done = ach["name"] in unlocked
        progress = f"{streak}/{ach['streak']}天" if ach.get("streak") else ""
        result.append({
            "badge": ach["badge"],
            "name": ach["name"],
            "desc": ach["desc"],
            "unlocked": done,
            "progress": progress,
        })
    
    return result


if __name__ == "__main__":
    print("=== 每日打卡模块测试 ===")
    
    # 模拟早上打卡
    r1 = checkin("morning")
    print(f"早打卡: {json.dumps(r1, ensure_ascii=False)}")
    
    # 模拟中午打卡
    r2 = checkin("afternoon")
    print(f"午打卡: {json.dumps(r2, ensure_ascii=False)}")
    
    # 模拟晚上打卡
    r3 = checkin("evening")
    print(f"晚打卡: {json.dumps(r3, ensure_ascii=False)}")
    
    # 查看状态
    status = get_checkin_status()
    print(f"打卡状态: {json.dumps(status, ensure_ascii=False)}")
    
    # 提醒
    reminder = get_checkin_reminder()
    print(f"提醒: {reminder}")
