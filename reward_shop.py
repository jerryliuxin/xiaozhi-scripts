"""奖励商店模块 — 积分兑换系统

增强版：
1. 家长确认机制（防止米奇随意兑换）
2. 兑换记录可追溯
3. 支持自定义奖励
4. 兑换后自动通知家长
"""

import sys
import os
import json
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REWARD_CONFIG_FILE = os.path.join(BASE_DIR, "reward_config.json")

# 奖励商店
# === 奖励商店配置 ===
# 优先从 reward_shop.json 加载，如无则使用默认
SHOP_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reward_shop.json")

def _load_shop_from_json():
    """从 JSON 文件加载奖励配置。"""
    if os.path.exists(SHOP_DATA_FILE):
        try:
            with open(SHOP_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    raise FileNotFoundError(f"reward_shop.json 不存在或格式错误: {SHOP_DATA_FILE}")

def _save_shop_to_json(data):
    """保存奖励配置到 JSON 文件。"""
    try:
        tmp = SHOP_DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, SHOP_DATA_FILE)
    except Exception:
        pass

# 唯一数据源：只从 reward_shop.json 加载
REWARD_SHOP = _load_shop_from_json()



def _load_config():
    """加载自定义配置。"""
    if os.path.exists(REWARD_CONFIG_FILE):
        try:
            with open(REWARD_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"custom_rewards": [], "redemption_log": []}


def _save_config(config):
    """保存自定义配置。"""
    try:
        with open(REWARD_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_shop():
    """获取商店列表，标记哪些可兑换。"""
    score_info = game_engine.get_score()
    total = score_info["total_score"]
    config = _load_config()
    
    # 合并自定义奖励
    all_rewards = REWARD_SHOP + config.get("custom_rewards", [])
    
    items = []
    for r in all_rewards:
        items.append({
            **r,
            "can_redeem": r["cost"] <= total,
            "savings_needed": max(0, r["cost"] - total),
        })
    return items


def show_shop():
    """生成商店展示的 prompt。"""
    score_info = game_engine.get_score()
    total = score_info["total_score"]
    level = score_info["level"]

    shop_text = ""
    categories = {}
    for r in get_shop():
        cat = r.get("category", "其他")
        if cat not in categories:
            categories[cat] = []
        can = "✅ 可兑换" if r["can_redeem"] else f"❌ 还差{r['savings_needed']}分"
        shop_text += f"  {r['name']} — {r['cost']}分 — {can}\n"
        shop_text += f"    {r['desc']}\n\n"
        categories[cat].append(r)

    # 距离下一个奖励
    nearest = None
    for r in get_shop():
        if not r["can_redeem"]:
            nearest = r
            break

    prompt = f"""【🎁 积分奖励商店】

Mickey当前积分: {total} | 等级: {level}
连续学习: {score_info['streak_count']}天
已兑换: {score_info.get('total_redeemed', 0)}次

{shop_text}
"""
    if nearest:
        prompt += f"🎯 下一个可兑换目标: {nearest['name']}（还需 {nearest['savings_needed']} 分）\n"
    else:
        prompt += "🎉 所有奖励都已兑换！继续学习解锁新奖励吧！\n"
    
    prompt += f"""📊 积分赚取速度参考：
  - 剑桥英语教材: 15分/次
  - 口语练习: 20分/次
  - 整理房间: 15分/次
  - 每日任务全完成: +{game_engine.DAILY_COMPLETE_BONUS}分

💡 米奇可以告诉家长想兑换哪个奖励，家长确认后我来扣积分！
"""
    return prompt


def redeem_reward(reward_id, parent_confirmed=False):
    """兑换奖励（需要家长确认）。

    流程：
    1. 查找奖励
    2. 家长确认检查
    3. 验证 total_score >= cost
    4. 扣减 total_score
    5. 在 history 中添加一条 "redeemed_{reward_id}" 条目（total 为负数）
    6. 记录兑换历史（兑换日期、奖励名称、消耗积分）
    7. 持久化到 game_data.json 和 config
    8. 返回结果
    """
    from datetime import datetime as _dt

    config = _load_config()
    score_info = game_engine.get_score()
    total = score_info["total_score"]

    # 查找奖励
    reward = None
    all_rewards = REWARD_SHOP + config.get("custom_rewards", [])
    for r in all_rewards:
        if r["id"] == reward_id:
            reward = r
            break

    if not reward:
        return {"error": "奖励不存在"}

    # 检查是否需要家长确认
    if reward.get("parent_confirm", True) and not parent_confirmed:
        reward_name = reward["name"]
        reward_cost = reward["cost"]
        return {
            "error": "⚠️ 此奖励需要家长确认",
            "reward_name": reward_name,
            "cost": reward_cost,
            "message": f"请家长确认后告诉我：'家长确认兑换{reward_name}'",
        }

    if total < reward["cost"]:
        return {
            "error": f"积分不足！需要 {reward['cost']} 分，当前 {total} 分",
            "needed": reward["cost"],
            "have": total,
        }

    # 扣减积分（直接操作 game_data.json）
    data = game_engine._load()
    data["total_score"] = max(0, data["total_score"] - reward["cost"])

    # 在 history 中添加一条 "redeemed_{reward_id}" 条目（total 为负数，等于 -cost）
    now_str = _dt.now().strftime("%H:%M:%S")
    history_entry = {
        "date": date.today().isoformat(),
        "time": now_str,
        "activity": f"redeemed_{reward_id}",
        "label": f"兑换奖励: {reward['name']}",
        "base_points": -reward["cost"],
        "effective_points": -reward["cost"],
        "streak_bonus": 0,
        "multi_bonus": 0,
        "bonus": 0,
        "total": -reward["cost"],
        "reason": "兑换奖励",
    }
    data["history"].append(history_entry)

    # 记录兑换到 redeemed_rewards
    record = {
        "reward_id": reward_id,
        "name": reward["name"],
        "cost": reward["cost"],
        "date": date.today().isoformat(),
        "parent_confirmed": parent_confirmed,
    }
    data.setdefault("redeemed_rewards", []).append(record)
    game_engine._save(data)

    # 记录到配置（持久化）
    config.setdefault("redemption_log", []).append(record)
    _save_config(config)

    return {
        "success": True,
        "reward": reward["name"],
        "cost": reward["cost"],
        "description": reward["desc"],
        "remaining": data["total_score"],
        "level": game_engine._get_current_level(data["total_score"]),
        "message": f"🎉 成功兑换！{reward['name']} - 消耗{reward['cost']}分，剩余{data['total_score']}分",
    }


def add_custom_reward(name, cost, desc, category="其他"):
    """家长添加自定义奖励。"""
    config = _load_config()
    new_reward = {
        "id": f"custom_{len(config.get('custom_rewards', [])) + 1}",
        "name": name,
        "cost": cost,
        "desc": desc,
        "category": category,
        "parent_confirm": True,
        "is_custom": True,
    }
    config.setdefault("custom_rewards", []).append(new_reward)
    _save_config(config)
    return {"success": True, "reward": new_reward}


if __name__ == "__main__":
    print("=== 奖励商店测试 ===")
    print(show_shop())
