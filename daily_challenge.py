"""每日任务+问答系统 — 每日挑战


import logging

logger = logging.getLogger("xiaozhi_edu")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)

增强版：
1. 使用 game_engine.get_daily_tasks 作为权威数据源
2. 支持每日挑战答题（每日一道趣味题）
3. 支持家长自定义任务
4. 支持任务进度追踪
"""

import random
import sys
import os
from datetime import date
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



# 每日挑战活动池
CHALLENGE_POOL = [
    {"id": "unlock",     "label": "剑桥英语教材",  "points": 15},
    {"id": "mickey_f1",  "label": "F1日常聊天",    "points": 10},
    {"id": "story_song", "label": "讲故事",         "points": 12},
    {"id": "explain",    "label": "为什么问答",     "points": 8},
    {"id": "adventure",  "label": "互动冒险",       "points": 20},
    {"id": "math_logic", "label": "数学逻辑",       "points": 15},
    {"id": "english_quiz","label": "英语闯关",      "points": 15},
    {"id": "chinese_recite","label": "国学背书",    "points": 15},
    {"id": "knowledge",  "label": "知识问答",       "points": 10},
    {"id": "speech_practice","label": "口语练习",   "points": 20},
    {"id": "clean_room", "label": "整理房间",       "points": 15},
    {"id": "proactive",  "label": "主动学习",       "points": 10},
    {"id": "daily_quiz", "label": "每日趣味问答",   "points": 10},
]

# 每日挑战答题题库
QUIZ_POOL = [
    # 科学
    {"q": "光从太阳到地球需要多长时间？A) 8分钟 B) 8小时 C) 8秒", "a": "A", "explain": "光速约30万公里/秒，太阳到地球约1.5亿公里，所以需要约8分钟！"},
    {"q": "水在多少摄氏度沸腾？A) 90°C B) 100°C C) 110°C", "a": "B", "explain": "在标准大气压下，水在100°C沸腾。高山上气压低，沸点会稍低！"},
    {"q": "人体最大的器官是什么？A) 心脏 B) 肝脏 C) 皮肤", "a": "C", "explain": "皮肤是人体最大的器官！成年人的皮肤面积约1.5-2平方米！"},
    {"q": "蜜蜂有多少种颜色？A) 1种 B) 2种 C) 3种", "a": "B", "explain": "蜜蜂只有黄色和黑色两种颜色！这有助于警告捕食者。"},
    {"q": "哪种气体是植物光合作用需要的？A) 氧气 B) 二氧化碳 C) 氮气", "a": "B", "explain": "植物用二氧化碳和水，在阳光下制造氧气和糖！"},
    # 历史/文化
    {"q": "中国古代四大发明不包括以下哪一项？A) 造纸术 B) 火药 C) 电灯", "a": "C", "explain": "四大发明是造纸术、印刷术、火药和指南针！"},
    {"q": "长城主要是哪个朝代修建的？A) 汉朝 B) 明朝 C) 唐朝", "a": "B", "explain": "我们现在看到的大部分长城是明朝修的，但最早从秦朝就开始修了！"},
    # 英语
    {"q": "'Uncomfortable'有几个音节？A) 4 B) 5 C) 6", "a": "C", "explain": "Un-com-for-tab-ble，6个音节！"},
    {"q": "Which word is a synonym for 'happy'? A) Sad B) Joyful C) Angry", "a": "B", "explain": "'Joyful' means feeling great pleasure — same as happy!"},
    {"q": "'She runs ___ than me.' A) fast B) faster C) fastest", "a": "B", "explain": "Comparing two things, use the comparative: faster!"},
    # 逻辑
    {"q": "一个农场有鸡和兔子共10只，头共10个，脚共26只。有几只兔子？A) 3 B) 4 C) 5", "a": "B", "explain": "设兔子x只，鸡(10-x)只。4x + 2(10-x) = 26 → x = 4只兔子！"},
    {"q": "如果今天是星期五，100天后是星期几？A) 星期五 B) 星期六 C) 星期日", "a": "C", "explain": "100 ÷ 7 = 14余2，星期五加2天 = 星期日！"},
    {"q": "一根绳子对折3次后，从中间剪断，会变成几段？A) 4段 B) 5段 C) 8段", "a": "B", "explain": "对折3次=8层，从中间剪 = 5段（中间1段+两端各2段）！"},
    # 地理
    {"q": "世界上最大的洲是？A) 非洲 B) 亚洲 C) 北美洲", "a": "B", "explain": "亚洲面积约4400万平方公里，占地球陆地面积的29.4%！"},
    {"q": "尼罗河在哪个洲？A) 亚洲 B) 非洲 C) 南美洲", "a": "B", "explain": "尼罗河在非洲，全长约6650公里，是世界上最长的河流之一！"},
]


def generate_daily_challenge():
    """生成今日挑战任务（随机5项，每天固定一次）。"""
    today = date.today().isoformat()
    seed = sum(ord(c) for c in today)
    random.seed(seed)
    selected = random.sample(CHALLENGE_POOL, min(5, len(CHALLENGE_POOL)))
    random.seed(None)
    return selected


def get_today_progress():
    """获取今日挑战进度（从 game_engine 权威数据源）。"""
    daily = game_engine.get_daily_tasks()
    if isinstance(daily, list):
        tasks = daily
        # Derive completed status: all required tasks done?
        required_ids = {"unlock", "english_quiz", "math_logic", "chinese_recite", "speech_practice"}
        done_ids = set()
        for t in tasks:
            if isinstance(t, dict):
                done_ids.add(t.get("id", ""))
        completed = required_ids.issubset(done_ids)
        return {
            "tasks": tasks,
            "completed": completed,
            "daily_bonus_claimed": False,
        }
    return {
        "tasks": daily.get("tasks", []),
        "completed": daily.get("completed", False),
        "daily_bonus_claimed": daily.get("daily_bonus_claimed", False),
    }


def get_daily_quiz():
    """获取今日趣味挑战答题。"""
    today = date.today().isoformat()
    seed = sum(ord(c) for c in today)
    random.seed(seed)
    quiz = random.choice(QUIZ_POOL)
    random.seed(None)
    return {
        "question": quiz["q"],
        "answer": quiz["a"],
        "explanation": quiz["explain"],
        "points": 10,
    }


def get_daily_quiz_prompt():
    """生成每日挑战答题的 prompt。"""
    selected = generate_daily_challenge()
    quiz = get_daily_quiz()
    total_possible = sum(item["points"] for item in selected) + game_engine.DAILY_COMPLETE_BONUS

    task_list = "\n".join([f"  {i+1}. [{item['points']}分] {item['label']} ({item['id']})"
                           for i, item in enumerate(selected)])

    score_info = game_engine.get_score()

    prompt = f"""【🎯 每日挑战任务】

今天有 {len(selected)} 个学习任务！
每完成一项都可以获得积分，全部完成还有额外奖励 {game_engine.DAILY_COMPLETE_BONUS} 分！

今日挑战：
{task_list}

💰 全部完成可获得: +{game_engine.DAILY_COMPLETE_BONUS}分（总计+{total_possible}分）
📊 当前积分: {score_info['total_score']} | 等级: {score_info['level']}
🔥 连胜: {score_info['streak_count']}天

【🧠 今日趣味问答】
问题: {quiz['question']}
答对可得 10 分！
提示: {quiz['explanation'][:50]}...

执行步骤：
1. 用兴奋的语气介绍今日挑战
2. 引导米奇一项一项完成
3. 每完成一项在 edu_backend 中调用对应工具
4. 全部完成后调用 daily_challenge.mark_daily_complete() 领取额外奖励
5. 展示最终报告和成就

加油！米奇是最棒的！🌟
"""
    return prompt


def answer_daily_quiz(answer):
    """
    核对每日答题答案，答对则记录积分。
    
    answer: 用户提交的答案（如 "A"）
    返回：答对/答错信息 + 积分记录
    """
    quiz = get_daily_quiz()
    correct_answer = quiz["answer"]
    is_correct = answer.strip().upper() == correct_answer

    if is_correct:
        # 答对：记录积分
        result = game_engine.record_activity(
            "daily_quiz",
            points=10,
            label="每日趣味问答"
        )
        if "error" in result:
            return {
                "correct": True,
                "correct_answer": correct_answer,
                "question": quiz["question"],
                "explanation": quiz["explanation"],
                "error": result["error"],
                "note": "积分已达今日上限",
            }
        result["correct"] = True
        result["correct_answer"] = correct_answer
        result["question"] = quiz["question"]
        result["explanation"] = quiz["explanation"]
        result["message"] = f"答对了！正确答案是 {correct_answer}！+10分！🎉"
        return result
    else:
        return {
            "correct": False,
            "your_answer": answer.strip().upper(),
            "correct_answer": correct_answer,
            "question": quiz["question"],
            "explanation": quiz["explanation"],
            "message": f"答错了哦～你选了 {answer.strip().upper()}，正确答案是 {correct_answer}。别灰心，明天再来！"
        }


def mark_daily_complete():
    """标记每日任务全部完成，发放额外奖励。"""
    result = game_engine.record_activity(
        "daily_complete",
        points=game_engine.DAILY_COMPLETE_BONUS,
        label="每日任务全完成"
    )
    result["message"] = f"太棒了！所有挑战都完成了！额外奖励 {game_engine.DAILY_COMPLETE_BONUS} 分！🎉"
    return result


if __name__ == "__main__":
    print("=== 每日挑战测试 ===")
    print("今日挑战:")
    for item in generate_daily_challenge():
        print(f"  {item['label']}: {item['points']}分")
    print()
    print("趣味问答:")
    quiz = get_daily_quiz()
    print(f"  Q: {quiz['question']}")
    print(f"  A: {quiz['answer']}")
    print(f"  解释: {quiz['explanation']}")

# ============================================================
# 增强版鼓励语
# ============================================================

ENRICHED_ENCOURAGEMENTS = {
    "unlock": [
        "英语教材学习真认真！", "剑桥英语继续加油！", "阅读时间到，米奇最棒了！",
        "今天的英语时间好充实！", "又解锁了新内容，太厉害了！",
    ],
    "speech_practice": [
        "口语练习开始啦！", "大声说出来，发音越来越标准！",
        "英语对话练习好认真！", "开口说英语，你超棒的！",
    ],
    "daily_quiz": [
        "知识问答时间到！", "动脑筋时间！", "趣味问答开始咯！",
        "今天知道新东西了吗？", "🧠 知识小达人！",
    ],
    "daily_complete": [
        "🎉 太棒了！今天全部任务都完成了！", "🌟 超级米奇！今日任务全通关！",
        "🏆 满分表现！所有任务都完成！", "💪 完美的一天！全部搞定！",
    ],
}

def get_enriched_message(task_id, streak_count=0):
    """根据任务类型和连胜天数获取丰富鼓励语。"""
    messages = ENRICHED_ENCOURAGEMENTS.get(task_id, [])
    if not messages:
        return "做得好！继续加油！"
    
    # 连胜天数增强
    if streak_count >= 30:
        suffixes = [
            f"🏆 第 {streak_count} 天！你是真正的学习冠军！",
            f"👑 连续 {streak_count} 天！你是榜样！",
        ]
    elif streak_count >= 7:
        suffixes = [
            f"🔥 连续 {streak_count} 天！太厉害了！",
            f"💪 坚持 {streak_count} 天了，真棒！",
        ]
    elif streak_count >= 3:
        suffixes = [
            f"✨ 连续 {streak_count} 天！",
            f"🌟 坚持了 {streak_count} 天！",
        ]
    else:
        suffixes = ["", ""]
    
    import random
    return random.choice(messages) + random.choice(suffixes)
