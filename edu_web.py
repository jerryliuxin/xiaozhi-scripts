"""edu_web.py — 小智教育积分管理系统 Web API (FastAPI)

提供 HTTP API 供前端/小智客户端调用。
启动: python3.11 edu_web.py
访问: http://0.0.0.0:8000/

API 规范参考 192.168.100.41 上的完整实现，统一响应格式:
  {"success": true, "code": 200, "message": "成功", "data": {...}}
"""

import sys
import os
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, List
import uvicorn

# 导入教育模块
import edu_backend

app = FastAPI(title="小智教育积分管理系统", version="2.0")

# CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 统一响应工具
# ============================================================

def ok(data=None, message="成功"):
    return {"success": True, "code": 200, "message": message, "data": data}

def err(message="错误", code=400):
    return JSONResponse(
        status_code=code,
        content={"success": False, "code": code, "message": message, "data": None}
    )

# ============================================================
# 数据持久化（从 game_data.json 读取，同时管理额外数据）
# ============================================================

GAME_DATA_PATH = os.path.join(base_dir, "game_data.json")

def load_game_data():
    """加载游戏数据"""
    if os.path.exists(GAME_DATA_PATH):
        try:
            with open(GAME_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_score": 0, "history": [], "streak_count": 0, "streak_dates": [],
            "penalty_multiplier": 1.0, "redeemed_rewards": [], "achievements_unlocked": [],
            "chore_count": 0, "creative_count": 0, "teach_count": 0,
            "exercise_count": 0, "checkin_count": 0, "last_play_date": None}

def save_game_data(data):
    """保存游戏数据（原子写入）"""
    try:
        tmp = GAME_DATA_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, GAME_DATA_PATH)
        return True
    except Exception:
        return False

# 额外的管理数据（exercise/checkin/redeemed 等独立追踪）
MANAGED_DATA_PATH = os.path.join(base_dir, "xiaozhi_managed.json")

def load_managed_data():
    """加载管理的额外数据"""
    if os.path.exists(MANAGED_DATA_PATH):
        try:
            with open(MANAGED_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"exercises": [], "checkins": [], "redeemed": [], "shop_items": []}

def save_managed_data(data):
    """保存管理数据"""
    try:
        tmp = MANAGED_DATA_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, MANAGED_DATA_PATH)
        return True
    except Exception:
        return False

# ============================================================
# 数据导出/导入
# ============================================================

def export_all_data():
    """导出所有数据"""
    return {
        "game_data": load_game_data(),
        "managed_data": load_managed_data(),
        "exported_at": __import__('datetime').datetime.now().isoformat()
    }

def import_all_data(new_data):
    """导入所有数据"""
    if "game_data" in new_data:
        save_game_data(new_data["game_data"])
    if "managed_data" in new_data:
        save_managed_data(new_data["managed_data"])
    return {"message": "数据导入成功"}

# ============================================================
# 根路径 — 返回 API 文档
# ============================================================

@app.get("/", response_class=HTMLResponse)
def index():
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>小智教育积分管理系统</title>
<style>
body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }
h1 { color: #2c3e50; } h2 { color: #3498db; margin-top: 30px; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 14px; }
th { background: #f8f9fa; }
.method { display: inline-block; padding: 2px 8px; border-radius: 3px; color: #fff; font-size: 12px; font-weight: bold; min-width: 45px; text-align: center; }
.GET { background: #27ae60; } .POST { background: #2980b9; } .PUT { background: #f39c12; } .DELETE { background: #e74c3c; }
.path { font-family: monospace; color: #2c3e50; }
</style></head><body>
<h1>🤖 小智教育积分管理系统 v2.0</h1>
<p><strong>文档:</strong> <a href="/docs">Swagger UI</a> | <a href="/openapi.json">OpenAPI</a> | <a href="/health">Health</a></p>
<h2>API 端点</h2>
<table><tr><th>方法</th><th>路径</th><th>说明</th></tr>
<tr><td><span class="method GET">GET</span></td><td class="path">/api/dashboard</td><td>仪表盘数据</td></tr>
<tr><td><span class="method GET">GET</span></td><td class="path">/api/score</td><td>完整积分信息</td></tr>
<tr><td><span class="method GET">GET</span></td><td class="path">/api/history</td><td>积分历史</td></tr>
<tr><td><span class="method GET">GET</span></td><td class="path">/api/daily/{date_str}</td><td>指定日期记录</td></tr>
<tr><td><span class="method GET">GET</span></td><td class="path">/api/exercise</td><td>运动统计</td></tr>
<tr><td><span class="method POST">POST</span></td><td class="path">/api/exercise</td><td>添加运动</td></tr>
<tr><td><span class="method GET">GET</span></td><td class="path">/api/checkin/{date_str}</td><td>打卡状态</td></tr>
<tr><td><span class="method GET">GET</span></td><td class="path">/api/shop</td><td>商店奖励列表</td></tr>
<tr><td><span class="method POST">POST</span></td><td class="path">/api/shop/redeem/{reward_id}</td><td>兑换奖励</td></tr>
<tr><td><span class="method GET">GET</span></td><td class="path">/api/redeemed</td><td>兑换记录</td></tr>
<tr><td><span class="method POST">POST</span></td><td class="path">/api/data/export</td><td>导出所有数据</td></tr>
<tr><td><span class="method POST">POST</span></td><td class="path">/api/data/import</td><td>导入所有数据</td></tr>
<tr><td><span class="method GET">GET</span></td><td class="path">/health</td><td>健康检查</td></tr>
</table>
</body></html>"""
    return html

# ============================================================
# /health
# ============================================================

@app.get("/health")
def health():
    return ok({"status": "ok", "service": "xiaozhi-education-api", "version": "2.0"})

# ============================================================
# /api/dashboard — 仪表盘
# ============================================================

@app.get("/api/dashboard")
def api_dashboard():
    """获取仪表盘数据（只统计英语学习相关积分）"""
    game_data = load_game_data()
    managed = load_managed_data()
    
    total_score = game_data.get("total_score", 0)
    level = edu_backend.game_engine._get_current_level(total_score)
    streak_count = game_data.get("streak_count", 0)
    streak_dates = game_data.get("streak_dates", [])
    achievements = game_data.get("achievements_unlocked", [])
    today = __import__('datetime').date.today().isoformat()
    
    # 今日学习记录
    today_learning = []
    for h in game_data.get("history", []):
        if h.get("date") == today and h.get("activity") in edu_backend.LEARNING_POINTS:
            today_learning.append({
                "date": h["date"],
                "activity": h["activity"],
                "label": h.get("label", h["activity"]),
                "base_points": h.get("base_points", 0),
                "effective_points": h.get("effective_points", 0),
                "streak_bonus": h.get("streak_bonus", 0),
                "multi_bonus": h.get("multi_bonus", 0),
                "bonus": h.get("bonus", 0),
                "total": h.get("total", 0),
            })
    
    return ok({
        "total_score": total_score,
        "level": level,
        "streak_count": streak_count,
        "streak_dates": streak_dates,
        "today_activities": {"学习": today_learning},
        "exercises": [e for e in managed.get("exercises", []) if e.get("date") == today],
        "checkins": [c for c in managed.get("checkins", []) if c.get("date") == today],
    })

# ============================================================
# /api/score — 完整积分信息
# ============================================================

@app.get("/api/score")
def api_score():
    """获取完整积分信息"""
    game_data = load_game_data()
    total_score = game_data.get("total_score", 0)
    score_info = {
        "total_score": total_score,
        "level": edu_backend.game_engine._get_current_level(total_score),
        "streak_count": game_data.get("streak_count", 0),
        "penalty_multiplier": game_data.get("penalty_multiplier", 1.0),
        "streak_dates": game_data.get("streak_dates", []),
        "achievements": [a for a in __import__('json').loads(__import__('json').dumps(edu_backend.ACHIEVEMENTS)) if total_score >= a["score"]],
        "special_achievements": game_data.get("achievements_unlocked", []),
        "chore_count": game_data.get("chore_count", 0),
        "creative_count": game_data.get("creative_count", 0),
        "teach_count": game_data.get("teach_count", 0),
        "exercise_count": game_data.get("exercise_count", 0),
        "checkin_count": game_data.get("checkin_count", 0),
    }
    
    # 每日任务
    daily_tasks = __import__('json').loads(__import__('json').dumps(edu_backend.DAILY_TASKS)).items()
    today = __import__('datetime').date.today().isoformat()
    tasks_list = []
    for tid, tinfo in edu_backend.DAILY_TASKS.items():
        completed = any(
            h.get("date") == today and (h.get("activity") == tid or 
            (tid == "daily_study" and h.get("activity") in ["unlock", "english_quiz", "chinese_recite"]) or
            (tid == "daily_speech" and h.get("activity") == "speech_practice") or
            (tid == "daily_knowledge" and h.get("activity") in ["knowledge", "explain"]))
            for h in game_data.get("history", [])
        )
        tasks_list.append({"id": tid, "label": tinfo["label"], "points": tinfo["base"], "completed": completed})
    
    score_info["daily_tasks"] = {"tasks": tasks_list, "completed": all(t["completed"] for t in tasks_list),
                                 "daily_bonus_claimed": game_data.get("daily_bonus_claimed", False)}
    
    # 可兑换奖励
    available_rewards = [r for r in edu_backend.REWARD_SHOP if r["cost"] <= total_score]
    score_info["available_rewards"] = available_rewards
    score_info["total_redeemed"] = len(game_data.get("redeemed_rewards", []))
    
    # 商店物品
    managed = load_managed_data()
    shop_items = managed.get("shop_items", edu_backend.REWARD_SHOP)
    
    # 历史记录摘要
    history = game_data.get("history", [])
    history_summary = {
        "total_records": len(history),
        "total_earnings": total_score,
        "history": history[-20:]  # 最近20条
    }
    
    return ok({
        "score_info": score_info,
        "shop_items": shop_items,
        "history_summary": history_summary,
    })

# ============================================================
# /api/history — 积分历史
# ============================================================

@app.get("/api/history")
def api_history(limit: int = Query(50, ge=1, le=200)):
    """获取积分历史（只返回英语学习相关活动）"""
    game_data = load_game_data()
    history = game_data.get("history", [])
    
    # 只保留学习相关活动
    learning_types = set(edu_backend.LEARNING_POINTS.keys())
    learning_types.add("daily_complete")
    learning_history = [h for h in history if h.get("activity") in learning_types]
    
    return ok({
        "activities": learning_history[-limit:],
        "exercises": __import__('json').loads(__import__('json').dumps(managed.get("exercises", [])[-limit:])),
        "checkins": __import__('json').loads(__import__('json').dumps(managed.get("checkins", [])[-limit:])),
        "total_available": len(learning_history),
    })

# ============================================================
# /api/history/activities/{index} — 编辑/删除活动记录
# ============================================================

@app.put("/api/history/activities/{index}")
async def edit_activity_record(index: int, request: Request):
    """编辑积分历史中的活动记录"""
    game_data = load_game_data()
    history = game_data.get("history", [])
    
    if index < 0 or index >= len(history):
        return err("索引超出范围")
    
    body = await request.json()
    activity_type = body.get("activity_type")
    points = body.get("points")
    bonus = body.get("bonus")
    label = body.get("label")
    
    if activity_type is not None:
        history[index]["activity"] = activity_type
    if points is not None:
        history[index]["base_points"] = points
    if bonus is not None:
        history[index]["bonus"] = bonus
    if label is not None:
        history[index]["label"] = label
    
    history[index]["total"] = (history[index].get("base_points", 0) + 
                                history[index].get("streak_bonus", 0) + 
                                history[index].get("multi_bonus", 0) + 
                                history[index].get("bonus", 0))
    
    game_data["history"] = history
    save_game_data(game_data)
    
    return ok({"message": "活动记录已更新", "record": history[index]})

@app.delete("/api/history/activities/{index}")
def delete_activity_record(index: int):
    """删除积分历史中的活动记录"""
    game_data = load_game_data()
    history = game_data.get("history", [])
    
    if index < 0 or index >= len(history):
        return err("索引超出范围")
    
    deleted = history.pop(index)
    
    # 调整总积分
    game_data["total_score"] = max(0, game_data["total_score"] - deleted.get("total", 0))
    game_data["history"] = history
    save_game_data(game_data)
    
    return ok({"message": "活动记录已删除", "deleted": deleted})

# ============================================================
# /api/history/exercises/{index} — 编辑/删除运动记录
# ============================================================

@app.put("/api/history/exercises/{index}")
async def edit_exercise_record(index: int, request: Request):
    """编辑运动记录"""
    managed = load_managed_data()
    exercises = managed.get("exercises", [])
    
    if index < 0 or index >= len(exercises):
        return err("索引超出范围")
    
    body = await request.json()
    if "label" in body:
        exercises[index]["label"] = body["label"]
    if "duration_minutes" in body:
        exercises[index]["duration_minutes"] = body["duration_minutes"]
    if "count" in body:
        exercises[index]["count"] = body["count"]
    
    managed["exercises"] = exercises
    save_managed_data(managed)
    return ok({"message": "运动记录已更新", "record": exercises[index]})

@app.delete("/api/history/exercises/{index}")
def delete_exercise_record(index: int):
    """删除运动记录"""
    managed = load_managed_data()
    exercises = managed.get("exercises", [])
    
    if index < 0 or index >= len(exercises):
        return err("索引超出范围")
    
    deleted = exercises.pop(index)
    managed["exercises"] = exercises
    save_managed_data(managed)
    return ok({"message": "运动记录已删除", "deleted": deleted})

# ============================================================
# /api/history/checkins/{index} — 编辑/删除打卡记录
# ============================================================

@app.put("/api/history/checkins/{index}")
async def edit_checkin_record(index: int, request: Request):
    """编辑打卡记录"""
    managed = load_managed_data()
    checkins = managed.get("checkins", [])
    
    if index < 0 or index >= len(checkins):
        return err("索引超出范围")
    
    body = await request.json()
    for key in ["period", "period_label", "bonus", "time"]:
        if key in body:
            checkins[index][key] = body[key]
    
    managed["checkins"] = checkins
    save_managed_data(managed)
    return ok({"message": "打卡记录已更新", "record": checkins[index]})

@app.delete("/api/history/checkins/{index}")
def delete_checkin_record(index: int):
    """删除打卡记录"""
    managed = load_managed_data()
    checkins = managed.get("checkins", [])
    
    if index < 0 or index >= len(checkins):
        return err("索引超出范围")
    
    deleted = checkins.pop(index)
    managed["checkins"] = checkins
    save_managed_data(managed)
    return ok({"message": "打卡记录已删除", "deleted": deleted})

# ============================================================
# /api/daily/{date_str} — 指定日期记录
# ============================================================

@app.get("/api/daily/{date_str}")
def get_daily_records(date_str: str):
    """获取指定日期的完整记录"""
    game_data = load_game_data()
    managed = load_managed_data()
    
    history = [h for h in game_data.get("history", []) if h.get("date") == date_str]
    exercises = [e for e in managed.get("exercises", []) if e.get("date") == date_str]
    checkins = [c for c in managed.get("checkins", []) if c.get("date") == date_str]
    
    return ok({
        "date": date_str,
        "activities": history,
        "exercises": exercises,
        "checkins": checkins,
        "total": len(history) + len(exercises) + len(checkins),
    })

# ============================================================
# /api/daily/history — 日期范围历史
# ============================================================

@app.get("/api/daily/history")
def get_daily_history(start: str = Query("2024-01-01"), end: Optional[str] = Query(None)):
    """获取日期范围内的历史记录"""
    if end is None:
        end = __import__('datetime').date.today().isoformat()
    
    game_data = load_game_data()
    history = game_data.get("history", [])
    filtered = [h for h in history if start <= h.get("date", "") <= end]
    
    return ok({"records": filtered, "count": len(filtered)})

# ============================================================
# /api/exercise — 运动统计
# ============================================================

@app.get("/api/exercise")
def get_exercise_stats(period: str = Query("daily")):
    """获取运动统计"""
    managed = load_managed_data()
    exercises = managed.get("exercises", [])
    
    today = __import__('datetime').date.today().isoformat()
    
    if period == "daily":
        today_exercises = [e for e in exercises if e.get("date") == today]
        total_points = sum(e.get("total", 0) for e in today_exercises)
        total_minutes = sum(e.get("duration_minutes", 0) for e in today_exercises)
        status = {
            "date": today,
            "checkin_completed": len([c for c in managed.get("checkins", []) if c.get("date") == today]) >= 1,
            "exercise_count": len(today_exercises),
            "total_points": total_points,
            "total_minutes": total_minutes,
            "streak": _calc_exercise_streak(exercises, today),
            "recommended": _get_exercise_recommendation(total_minutes),
        }
    elif period == "weekly":
        week_start = (__import__('datetime').date.today() - __import__('datetime').timedelta(days=7)).isoformat()
        week_exercises = [e for e in exercises if e.get("date", "") >= week_start]
        status = {"period": "weekly", "count": len(week_exercises), "total_minutes": sum(e.get("duration_minutes", 0) for e in week_exercises)}
    else:
        month_start = __import__('datetime').date.today().replace(day=1).isoformat()
        month_exercises = [e for e in exercises if e.get("date", "") >= month_start]
        status = {"period": "monthly", "count": len(month_exercises), "total_minutes": sum(e.get("duration_minutes", 0) for e in month_exercises)}
    
    return ok({"period": period, "status": status, "recent_history": exercises[-5:]})

def _calc_exercise_streak(exercises, today):
    streak = 0
    d = __import__('datetime').date.today()
    for i in range(30):
        check_date = (d - __import__('datetime').timedelta(days=i)).isoformat()
        if any(e.get("date") == check_date for e in exercises):
            streak += 1
        else:
            break
    return streak

def _get_exercise_recommendation(minutes):
    if minutes < 10:
        return "试试跑步吧！每5分钟+5分，跑步锻炼心肺功能！"
    elif minutes < 30:
        return "不错！试试跳绳或球类运动，多一种类型+20分！"
    else:
        return "太棒了！坚持运动的好习惯！"

@app.post("/api/exercise")
async def add_exercise(request: Request):
    """添加运动记录"""
    try:
        body = await request.json()
    except Exception:
        return err("请求体格式错误")
    
    exercise_type = body.get("exercise_type", "other")
    duration_minutes = body.get("duration_minutes", 0)
    count = body.get("count", 0)
    label = body.get("label", f"运动-{exercise_type}")
    
    managed = load_managed_data()
    
    # 计算积分（每5分钟5分）
    earned_points = (duration_minutes // 5) * 5 if duration_minutes > 0 else 3  # 基础3分
    
    today = __import__('datetime').date.today().isoformat()
    record = {
        "date": today,
        "exercise": exercise_type,
        "label": label,
        "duration_minutes": duration_minutes,
        "count": count,
        "earned_points": earned_points,
        "streak_bonus": 0,
        "total": earned_points,
    }
    
    managed.setdefault("exercises", []).append(record)
    save_managed_data(managed)
    
    return ok({"message": "运动记录已添加", "record": record, "earned_points": earned_points})

# ============================================================
# /api/checkin/{date_str} — 打卡状态
# ============================================================

@app.get("/api/checkin/{date_str}")
def get_checkin(date_str: str):
    """获取指定日期的打卡状态"""
    managed = load_managed_data()
    checkins = [c for c in managed.get("checkins", []) if c.get("date") == date_str]
    
    completed_periods = [c.get("period") for c in checkins]
    pending_periods = [
        {"id": "morning", "label": "早上", "bonus": 5, "time_range": "6:00-12:00"},
        {"id": "afternoon", "label": "中午", "bonus": 5, "time_range": "12:00-18:00"},
        {"id": "evening", "label": "晚上", "bonus": 10, "time_range": "18:00-24:00"},
    ]
    pending_periods = [p for p in pending_periods if p["id"] not in completed_periods]
    
    today_points = sum(c.get("bonus", 0) for c in checkins)
    
    # 计算连续打卡
    streak = 0
    d = __import__('datetime').date.today()
    for i in range(30):
        check_date = (d - __import__('datetime').timedelta(days=i)).isoformat()
        if any(c.get("date") == check_date for c in managed.get("checkins", [])):
            streak += 1
        else:
            break
    
    return ok({
        "status": {
            "date": date_str,
            "checkin_count": len(checkins),
            "max_checkins": 3,
            "today_points": today_points,
            "streak": streak,
            "completed_periods": completed_periods,
            "pending_periods": pending_periods,
            "next_milestone": {"days": max(0, 3 - streak), "bonus": 10} if streak < 3 else None,
            "status_text": f"📅 今日打卡状态\n{'━'*32}\n💰 今日打卡积分：{today_points}分\n📊 已打卡 {len(checkins)}/3 次\n🔥 连续打卡：{streak}天",
        },
        "day_checkins": checkins,
    })

# ============================================================
# /api/shop — 商店
# ============================================================

@app.get("/api/shop")
def get_shop():
    """获取商店奖励列表"""
    managed = load_managed_data()
    shop_items = managed.get("shop_items", edu_backend.REWARD_SHOP)
    
    game_data = load_game_data()
    total_score = game_data.get("total_score", 0)
    
    # 兑换记录
    redeemed = managed.get("redeemed", [])
    
    return ok({
        "items": shop_items,
        "current_score": total_score,
        "redeemed_rewards": redeemed[-10:],  # 最近10条
    })

@app.post("/api/shop/redeem/{reward_id}")
def redeem_reward(reward_id: str):
    """兑换奖励"""
    managed = load_managed_data()
    shop_items = managed.get("shop_items", edu_backend.REWARD_SHOP)
    
    reward = next((r for r in shop_items if r["id"] == reward_id), None)
    if not reward:
        return err("奖励不存在")
    
    game_data = load_game_data()
    total = game_data.get("total_score", 0)
    
    if total < reward["cost"]:
        return err(f"积分不足，需要 {reward['cost']} 分，当前 {total} 分")
    
    game_data["total_score"] = total - reward["cost"]
    save_game_data(game_data)
    
    today = __import__('datetime').date.today().isoformat()
    redeemed_record = {
        "date": today,
        "time": __import__('datetime').datetime.now().strftime("%H:%M:%S"),
        "reward_id": reward_id,
        "name": reward["name"],
        "cost": reward["cost"],
    }
    
    managed.setdefault("redeemed", []).append(redeemed_record)
    save_managed_data(managed)
    
    return ok({"success": True, "points_spent": reward["cost"], "remaining": total - reward["cost"], "record": redeemed_record})

# ============================================================
# /api/shop/items — 管理商店物品
# ============================================================

@app.post("/api/shop/items")
async def create_reward_item(request: Request):
    """添加新奖励"""
    managed = load_managed_data()
    try:
        body = await request.json()
    except Exception:
        return err("请求体格式错误")
    
    name = body.get("name")
    cost = body.get("cost", 0)
    desc = body.get("desc", "")
    category = body.get("category", "其他")
    parent_confirm = body.get("parent_confirm", True)
    
    if not name or cost <= 0:
        return err("名称和积分必须有效")
    
    reward_id = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    
    item = {
        "id": reward_id,
        "name": name,
        "cost": cost,
        "desc": desc,
        "category": category,
        "parent_confirm": parent_confirm,
        "can_redeem": True,
        "savings_needed": 0,
    }
    
    managed.setdefault("shop_items", []).append(item)
    save_managed_data(managed)
    
    return ok({"message": "奖励已添加", "item": item})

@app.put("/api/shop/items/{reward_id}")
async def update_reward_item(reward_id: str, request: Request):
    """修改奖励"""
    managed = load_managed_data()
    shop_items = managed.get("shop_items", [])
    
    item = next((i for i in shop_items if i["id"] == reward_id), None)
    if not item:
        return err("奖励不存在")
    
    body = await request.json()
    for key in ["name", "cost", "desc", "category", "parent_confirm"]:
        if key in body:
            item[key] = body[key]
    
    save_managed_data(managed)
    return ok({"message": "奖励已更新", "item": item})

@app.delete("/api/shop/items/{reward_id}")
def delete_reward_item(reward_id: str):
    """删除奖励"""
    managed = load_managed_data()
    shop_items = managed.get("shop_items", [])
    
    new_items = [i for i in shop_items if i["id"] != reward_id]
    if len(new_items) == len(shop_items):
        return err("奖励不存在")
    
    managed["shop_items"] = new_items
    save_managed_data(managed)
    return ok({"message": "奖励已删除"})

# ============================================================
# /api/redeemed — 兑换记录
# ============================================================

@app.get("/api/redeemed")
def get_redeemed():
    """获取兑换记录"""
    managed = load_managed_data()
    redeemed = managed.get("redeemed", [])
    return ok({"redeemed": redeemed, "count": len(redeemed)})

@app.get("/api/redeemed/daily-summary")
def get_redeemed_daily_summary():
    """获取每日兑换统计"""
    managed = load_managed_data()
    redeemed = managed.get("redeemed", [])
    
    daily = {}
    for r in redeemed:
        d = r.get("date", "")
        cost = r.get("cost", 0)
        daily[d] = daily.get(d, 0) + cost
    
    return ok({"daily_summary": daily, "total_redeemed": sum(daily.values())})

@app.put("/api/redeemed/{index}")
async def update_redeemed_record(index: int, request: Request):
    """编辑兑换记录"""
    managed = load_managed_data()
    redeemed = managed.get("redeemed", [])
    
    if index < 0 or index >= len(redeemed):
        return err("索引超出范围")
    
    body = await request.json()
    for key in ["cost", "name"]:
        if key in body:
            old_value = redeemed[index].get(key, 0)
            new_value = body[key]
            # 调整积分
            delta = new_value - old_value
            game_data = load_game_data()
            game_data["total_score"] = max(0, game_data["total_score"] - delta)
            save_game_data(game_data)
            redeemed[index][key] = new_value
    
    save_managed_data(managed)
    return ok({"message": "兑换记录已更新", "record": redeemed[index]})

@app.delete("/api/redeemed/{index}")
def delete_redeemed_record(index: int):
    """删除兑换记录（并恢复积分）"""
    managed = load_managed_data()
    redeemed = managed.get("redeemed", [])
    
    if index < 0 or index >= len(redeemed):
        return err("索引超出范围")
    
    record = redeemed.pop(index)
    cost = record.get("cost", 0)
    
    # 恢复积分
    game_data = load_game_data()
    game_data["total_score"] += cost
    save_game_data(game_data)
    
    managed["redeemed"] = redeemed
    save_managed_data(managed)
    
    return ok({"message": "兑换记录已删除，积分已恢复", "refunded": cost})

# ============================================================
# /api/data/export — 导出数据
# ============================================================

@app.post("/api/data/export")
def export_data():
    """导出所有数据"""
    data = export_all_data()
    return ok({"export": data})

# ============================================================
# /api/data/import — 导入数据
# ============================================================

@app.post("/api/data/import")
async def import_data(request: Request):
    """导入数据"""
    try:
        body = await request.json()
    except Exception:
        return err("请求体格式错误")
    
    import_all_data(body.get("data", body))
    return ok({"message": "数据导入成功"})

# ============================================================
# 前端 SPA 路由
# ============================================================

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    """前端 SPA 路由"""
    if full_path == "" or full_path.startswith("api/") or full_path == "health" or full_path.endswith(".json"):
        return err("路径不存在", 404)
    return HTMLResponse("<h1>小智教育积分管理系统</h1><p>请使用 <a href='/docs'>Swagger UI</a> 或 API 端点</p>")

# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    print("🚀 小智教育积分管理系统 v2.0")
    print("   本地: http://localhost:8000")
    print("   文档: http://localhost:8000/docs")
    print("   健康: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)
