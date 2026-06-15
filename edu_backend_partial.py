"""edu_backend.py — 小智教育后端 + 自动积分记录

核心设计原则：
- xiaozhi 每次教育交互后**自动调用 game_engine.record_activity() 记录积分**
- 前端和管理面板只显示真实记录的数据

"""

import json
import os
import random
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_FILE = os.path.join(BASE_DIR, "kb", "knowledge.json")

import game_engine as ge
import speech_practice as sp
import daily_challenge as dch
import reward_shop as rs
import user_memory as user_memory_module
import q_memory as q_memory_module


# ============================================================
# _auto_record — 统一自动积分入口
# ============================================================

# 有积分的活动：action_name -> base_points
AUTO_RECORD_POINTS = {
    'unlock': 15,
    'english_quiz': 15,
    'story_listen': 10,
    'recitation': 15,
    'daily_quiz': 10,
    'daily_complete': 15,
    'daily_checkin_morning': 5,
    'daily_checkin_afternoon': 5,
    'daily_checkin_evening': 10,
    'daily_checkin_all': 15,
}

# 无积分但需记录的行为
ZERO_POINTS_TYPES = [
    'mickey_f1', 'story_song', 'knowledge', 'explain', 'adventure',
    'news_topic', 'praise', 'chore', 'unlock_english', 'speech_practice',
    'mickey_f1_chat', 'interactive_adventure', 'chinese_recitation',
    'unlock_daily_english_study',
]

def _auto_record(action, bonus=0):
    """自动记录一次活动到 game_engine。如果已达上限则静默跳过。"""
    if action in AUTO_RECORD_POINTS:
        base_points = AUTO_RECORD_POINTS[action]
    else:
        base_points = 0

    try:
        activity_type = action if action not in ('unlock_english', 'speech_practice') else action
        if activity_type == 'unlock_english':
            activity_type = 'unlock'
        elif activity_type == 'speech_practice':
            activity_type = 'speech'
        ge.record_activity(activity_type, points=base_points, bonus=bonus)
    except Exception:
        pass


# ============================================================
# 剑桥英语教材 (Cambridge Unlock Level 3)
# ============================================================

def get_unlock_content():
    _auto_record("unlock")
    user_memory_module.update_interaction("unlock_english")
    user_prompt = user_memory_module.get_user_prompt_prefix()

    unlock_topics = {
        "Animals": {"vocab": ("habitat", "endangered", "species", "predator", "prey"),
                    "grammar": "Present simple vs continuous",
                    "discussion": "Why do some animals migrate?"},
        "Environment": {"vocab": ("sustainable", "carbon footprint", "renewable energy", "conservation"),
                       "grammar": "Future forms",
                       "discussion": "What are the most effective ways to reduce plastic waste?"},
        "Transport": {"vocab": ("congestion", "commute", "infrastructure", "autonomous"),
                      "grammar": "Comparatives",
                      "discussion": "How do you think we will travel in 50 years?"},
        "Customs and Traditions": {"vocab": ("heritage", "celebration", "ritual", "generation"),
                                   "grammar": "Past simple vs continuous",
                                   "discussion": "What is the most important festival in your culture?"},
        "Health and Fitness": {"vocab": ("nutrition", "sedentary", "well-being", "metabolism"),
                               "grammar": "Modals of advice",
                               "discussion": "How does technology affect our physical health?"},
        "Discovery and Invention": {"vocab": ("breakthrough", "patent", "innovation", "prototype"),
                                    "grammar": "Passive voice",
                                    "discussion": "Which invention has changed the world the most?"},
        "Fashion": {"vocab": ("trend", "garment", "consumerism", "aesthetic"),
                    "grammar": "Used to / Would",
                    "discussion": "Is fast fashion damaging our planet?"},
        "Economics": {"vocab": ("inflation", "supply and demand", "currency", "investment"),
                      "grammar": "Conditionals",
                      "discussion": "How does inflation affect our daily lives?"},
    }

    topic = random.choice(list(unlock_topics.items()))
    topic_name, topic_data = topic

    game_info = ge.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info[\x27total_score\x27])} 分 | 等级:  {str(game_info[\x27level\x27])}\n")
    game_prefix += f"
连续学习: {str(game_info[\x27streak_count\x27])}\n"

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += "[System Instruction for Xiaozhi]
"

    prompt = (game_prefix + f"
You are now acting as an English tutor using Cambridge Unlock Level 3 (B1 Level).
Current Unit: Unit {topic_name}
Target Vocabulary: {', '.join(topic_data[\x27vocab\x27])}
Grammar Focus: {topic_data[\x27grammar\x27]}
Discussion Prompt: {topic_data[\x27discussion\x27]}

Your task:
1. Greet the user in English and introduce today's topic.
2. Teach 2 vocabulary words simply.
3. Ask the Discussion Prompt and wait for response. Keep sentences B1 level.
")

    return prompt

