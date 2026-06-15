"""激励系统总控 — 整合所有激励模块

提供统一的入口，让 edu_backend 可以调用各种激励功能。
每个函数返回结构化的 JSON，包含积分结果和提示语。"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_engine
import chore_tracker
import daily_challenge
import reward_shop
import speech_practice
import user_memory as um


# ========== 教育学习 ==========

def edu_learn(action, param=None):
    """教育学习记录（调用 edu_backend）。"""
    return game_engine.record_activity(
        action,
        label=game_engine.LEARNING_POINTS.get(action, {}).get("label", action)
    )


# ========== 家务 ==========

def chore_done(chore_name):
    """记录家务完成。"""
    return chore_tracker.record_chore(chore_name)


# ========== 积极行为 ==========

def positive_action(action):
    """记录积极行为（主动学习/教别人/创造/阅读）。"""
    info = game_engine.POSITIVE_POINTS.get(action, {"base": 5, "label": action})
    result = game_engine.record_activity(action, label=info["label"])
    return result


# ========== 惩罚 ==========

def penalty_apply(penalty_type, label=None):
    """记录惩罚。"""
    return game_engine.record_penalty(penalty_type, label)


# ========== 每日任务 ==========

def daily_tasks_status():
    """获取每日任务状态。"""
    return daily_challenge.get_today_progress()


def daily_tasks_list():
    """获取每日任务列表。"""
    return daily_challenge.generate_daily_challenge()


def daily_tasks_claim():
    """领取每日任务完成奖励。"""
    return daily_challenge.mark_daily_complete()


# ========== 奖励商店 ==========

def shop_view():
    """查看商店。"""
    return reward_shop.get_shop()


def shop_redeem(reward_id):
    """兑换奖励。"""
    return game_engine.redeem_reward(reward_id)


# ========== 积分查询 ==========

def get_full_score():
    """获取完整积分信息。"""
    return game_engine.get_score()


def get_today_report():
    """获取今日报告。"""
    return game_engine.get_report()


def get_history(limit=10):
    """获取近期历史。"""
    return game_engine.get_history(limit)


def get_chore_history(limit=10):
    """获取家务历史。"""
    return game_engine.get_chore_history(limit)


def get_today_activities():
    """获取今日活动分类。"""
    return game_engine.get_today_activities()


# ========== 儿童友好报告生成 ==========

def get_child_friendly_report():
    """
    生成儿童友好的报告（emoji + 简单语言）。
    用于小智直接对米奇说的话。
    """
    report = game_engine.get_report()
    score = report["total_score"]
    level = report["level"]
    streak = report["streak"]
    today_earn = report["today_earn"]
    today_penalty = report["today_penalty"]
    chores = report["chore_count"]

    # 根据得分给出鼓励语
    if score >= 3000:
        encouragement = "你已经是超级学霸了！继续加油，向传奇学霸冲刺！"
    elif score >= 1800:
        encouragement = "太厉害了！你是大家的学习榜样！"
    elif score >= 800:
        encouragement = "非常棒！你的努力正在让你变得越来越聪明！"
    elif score >= 250:
        encouragement = "干得不错！继续保持，你越来越棒了！"
    elif score >= 100:
        encouragement = "很棒！开始积累积分了，继续加油！"
    else:
        encouragement = "加油！每一天都是进步的机会！"

    # 连胜鼓励
    if streak >= 7:
        streak_msg = f"🔥 你连续学习了 {streak} 天！太自律了！"
    elif streak >= 3:
        streak_msg = f"🔥 连续 {streak} 天！继续保持就能拿连胜奖励了！"
    elif streak >= 1:
        streak_msg = f"📅 今天是你坚持学习的第 {streak} 天！"
    else:
        streak_msg = "开始你的学习之旅吧！坚持每天学习会有额外奖励！"

    # 今日earnings
    today_msg = f"今天获得了 {today_earn} 分"
    if today_penalty < 0:
        today_msg += f"，有 {today_penalty} 分惩罚（下次要更认真哦！）"

    # 家务
    chore_msg = ""
    if chores > 0:
        chore_msg = f"\n🧹 你一共帮助家里做了 {chores} 次家务，真能干！"

    # 下一目标
    next_streak = report.get("next_streak_milestone")
    if next_streak:
        streak_goal = f"下次连胜里程碑：连续 {next_streak['days']} 天可再拿 {next_streak['bonus']} 分"
    else:
        streak_goal = "🏆 连胜记录已保持到最高！"

    # 可兑换奖励
    redeemable = report.get("redeemable_rewards", [])
    if redeemable:
        reward_msg = f"🎁 你现在可以兑换 {len(redeemable)} 个奖励了：{', '.join([r['name'] for r in redeemable[:3]])}"
    else:
        nearest = reward_shop.REWARD_SHOP[0] if reward_shop.REWARD_SHOP else None
        if nearest:
            reward_msg = f"🎁 距离第一个奖励还差 {nearest['cost'] - score} 分！加油！"
        else:
            reward_msg = "🎁 太厉害了！所有奖励都可以兑换！"

    # 每日任务
    pending = report.get("pending_tasks", [])
    if pending:
        task_msg = f"\n📋 今天还有 {len(pending)} 个任务没完成：{', '.join([t.get('label', '') for t in pending])}"
    else:
        task_msg = "\n📋 今天所有任务都完成了！🎉"

    return (
        f"📊 米奇的学习报告\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 总积分: {score}\n"
        f"🏆 等级: {level}\n"
        f"{today_msg}\n"
        f"{streak_msg}\n"
        f"{streak_goal}\n"
        f"{chore_msg}\n"
        f"{task_msg}\n"
        f"{reward_msg}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{encouragement}\n"
    )


def get_prompt_prefix():
    """
    生成完整的激励系统前缀，注入到 edu_backend 的 prompt 中。
    包含：当前积分、等级、连胜、任务状态、可用奖励。
    """
    score_info = game_engine.get_score()
    total = score_info["total_score"]
    level = score_info["level"]
    streak = score_info["streak_count"]
    penalty_mult = score_info.get("penalty_multiplier", 1.0)

    pending_tasks = [t for t in score_info.get("daily_tasks", {}).get("tasks", []) if not t["completed"]]

    user_prefix = um.get_user_prompt_prefix()

    shop_list = ', '.join([r['name'] + '(' + str(r['cost']) + '分)' for r in reward_shop.REWARD_SHOP[:5]])

    prefix = f"""【激励系统状态】
Mickey当前积分: {total} | 等级: {level}
连续学习: {streak}天 | 断联惩罚: ×{penalty_mult}
今日待完成任务: {len(pending_tasks)}个

【积分规则】
学习：英语教材15分，口语20分，数学15分，国学15分，F1聊天10分
家务：整理房间15分，洗碗10分，倒垃圾8分，洗衣服12分
积极行为：主动学习+10分，教别人+15分，课外阅读+10分
惩罚：抄袭-10分，敷衍-5分，未完成每日任务-3分
连胜：3天+10分，7天+30分，30天+100分

【奖励商店】
{shop_list}...

"""
    if user_prefix:
        prefix += user_prefix + "\n"
    prefix += "[System Instruction for Xiaozhi]\n"
    return prefix


# ========== 快捷命令 ==========

def handle_command(command, param=None):
    """
    处理家长输入的快捷命令。
    
    命令格式：
    - "chore <家务名称>" — 记录家务
    - "positive <行为>" — 记录积极行为
    - "penalty <惩罚类型>" — 记录惩罚
    - "redeem <奖励ID>" — 兑换奖励
    - "report" — 生成报告
    - "shop" — 查看商店
    - "score" — 查询积分
    - "claim_daily" — 领取每日奖励
    """
    command = command.strip().lower()

    if command.startswith("chore "):
        chore_name = param or command[6:].strip()
        if chore_name:
            return chore_tracker.record_chore(chore_name)

    elif command.startswith("positive "):
        action = param or command[9:].strip()
        if action:
            return positive_action(action)

    elif command.startswith("penalty "):
        penalty_type = param or command[8:].strip()
        if penalty_type:
            return penalty_apply(penalty_type)

    elif command.startswith("redeem "):
        reward_id = param or command[7:].strip()
        if reward_id:
            return game_engine.redeem_reward(reward_id)

    elif command == "report":
        return get_child_friendly_report()

    elif command == "shop":
        return reward_shop.show_shop()

    elif command == "score":
        return get_full_score()

    elif command == "claim_daily":
        return daily_tasks_claim()

    elif command == "tasks":
        return daily_tasks_list()

    else:
        return {"error": f"未知命令: {command}", "help": [
            "chore <家务名称> — 记录家务",
            "positive <行为> — 记录积极行为",
            "penalty <类型> — 记录惩罚",
            "redeem <奖励ID> — 兑换奖励",
            "report — 生成儿童友好报告",
            "shop — 查看商店",
            "score — 查询积分",
            "claim_daily — 领取每日奖励",
            "tasks — 查看每日挑战",
        ]}
