"""口语练习模块 — 小智英语口语训练

增强版：
1. 支持3个难度等级（基础/中级/进阶）
2. 自动轮换句子避免重复
3. 支持评价和反馈（准确度/流利度/发音）
4. 支持自定义句子
"""

import random
import sys
import os
import json
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_engine

# ========== 配置 ==========
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "speech_history.json")

# 口语练习句子库（按等级分类）
SPOKEN_SENTENCES = {
    "基础": [
        "My name is Mickey and I am in fifth grade.",
        "I enjoy learning about science and history.",
        "One of my favorite subjects is English because it helps me communicate with the world.",
        "I like playing basketball with my friends after school.",
        "Reading books is one of my hobbies.",
        "My dream is to become a scientist when I grow up.",
        "I think robots will do most of the chores in the future.",
        "The best part of going to school is learning new things every day.",
    ],
    "中级": [
        "If I could travel anywhere in the world, I would visit the Great Wall of China.",
        "I believe that technology will help solve many of the world's problems in the future.",
        "F1 racing teaches us about teamwork, precision, and engineering.",
        "Learning a second language opens doors to understanding different cultures.",
        "The most important thing I learned this week was about the solar system.",
        "I think education should be fun, and games are a great way to learn.",
        "The Olympic Games bring people from all over the world together.",
        "In the future, I want to invent something that makes people's lives easier.",
    ],
    "进阶": [
        "Climate change is one of the biggest challenges facing our generation, and we need to act now.",
        "The invention of the internet revolutionized how humans share information and communicate globally.",
        "Success is not measured by wealth alone, but by the positive impact we make on others' lives.",
        "Exploring space not only satisfies our curiosity but also drives technological innovation on Earth.",
        "We should encourage critical thinking instead of simply memorizing facts in school.",
        "Artificial intelligence will change the way we work, but it cannot replace human creativity.",
        "The beauty of learning is that it never stops, no matter how old you get.",
        "I think the future of medicine lies in understanding the human brain and body at a molecular level.",
    ],
}

# 评价维度
EVAL_DIMENSIONS = ["准确度", "流利度", "发音"]

# 鼓励回复
ENCOURAGEMENTS = {
    "优秀": [
        "太棒了！发音越来越标准了！+5分！",
        "哇，说得跟母语者一样流利！+5分！",
        "太优秀了！每个词都清晰又准确！+5分！",
    ],
    "良好": [
        "Mickey真厉害，继续加油！+5分！",
        "真不错，表达流畅又准确！+5分！",
        "优秀！再来一个试试？+5分！",
    ],
    "需要改进": [
        "已经很棒了！再试一次会更好！+3分！",
        "不错，慢慢来，下次会更好的！+3分！",
        "进步很大！继续练会更好！+3分！",
    ],
}


def _load_history():
    """加载口语练习历史。"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"used_sentences": [], "total_sentences": 0, "total_score": 0}


def _save_history(history):
    """保存口语练习历史。"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_sentence(difficulty="中级"):
    """获取一句口语练习句子（避免重复）。"""
    history = _load_history()
    sentences = SPOKEN_SENTENCES.get(difficulty, SPOKEN_SENTENCES["中级"])
    used = history.get("used_sentences", [])
    
    # 筛选未使用的句子
    available = [s for s in sentences if s not in used]
    if not available:
        # 全部用过了，重置
        history["used_sentences"] = []
        available = sentences[:]
    
    selected = random.choice(available)
    history["used_sentences"].append(selected)
    history["total_sentences"] = history.get("total_sentences", 0) + 1
    _save_history(history)
    
    return selected


def get_daily_challenge(difficulty="中级"):
    """生成每日口语挑战的 prompt。"""
    sentences = SPOKEN_SENTENCES.get(difficulty, SPOKEN_SENTENCES["中级"])
    
    # 随机选取3句（不重复）
    available = sentences[:]
    random.shuffle(available)
    selected = available[:min(3, len(available))]
    sentence_list = "\n".join([f"  {i+1}. {s}" for i, s in enumerate(selected)])

    score_info = game_engine.get_score()

    prompt = f"""【🗣️ 口语练习挑战】

Mickey当前积分: {score_info['total_score']} | 等级: {score_info['level']}

【今日任务】
今天请跟读以下 {difficulty} 难度的英语句子，每读对一句加5分！

英语句子：
{sentence_list}

【评价标准】
- 准确度：单词发音是否正确
- 流利度：是否流畅不卡顿
- 发音：语音语调是否自然

执行步骤：
1. 用中文介绍今天的学习任务，鼓励 Mickey 大声朗读
2. 逐句引导 Mickey 跟读
3. 每句读完后给出鼓励 + 评价
4. 全部完成后总结，说 "太厉害了！完成了 {len(selected)} 句练习，获得 {len(selected) * 5} 分！"

注意：每读完一句，都要给予鼓励！
"""
    return prompt


def evaluate_and_score(completed_count, quality="good"):
    """家长确认完成，记录积分 + 评价。"""
    # quality: "excellent" / "good" / "needs_improvement"
    points_per_sentence = {"excellent": 5, "good": 5, "needs_improvement": 3}
    points = completed_count * points_per_sentence.get(quality, 5)
    
    result = game_engine.record_activity(
        "speech_practice",
        points=points,
        label=f"口语练习（{completed_count}句，{quality}）"
    )
    
    # 选择鼓励语
    pool = ENCOURAGEMENTS.get(
        "优秀" if quality == "excellent" else 
        "良好" if quality == "good" else 
        "需要改进",
        ENCOURAGEMENTS["良好"]
    )
    result["message"] = random.choice(pool)
    result["completed_sentences"] = completed_count
    result["quality"] = quality
    result["points_per_sentence"] = points_per_sentence.get(quality, 5)
    return result


def get_ongoing_challenge():
    """获取持续进行中的口语挑战状态。"""
    history = _load_history()
    sentences = SPOKEN_SENTENCES.get("中级", [])
    used = history.get("used_sentences", [])
    remaining = len(sentences) - len(used)
    if remaining < 0:
        remaining = len(sentences)
    
    return {
        "remaining": remaining,
        "total_practiced": history.get("total_sentences", 0),
        "sentence_list": sentences,
    }


def get_prompt_prefix():
    """生成口语练习注入的前缀（包含当前积分状态）。"""
    score_info = game_engine.get_score()
    history = _load_history()
    prefix = f"""【口语练习模式】
Mickey当前积分: {score_info['total_score']} | 等级: {score_info['level']}
连续学习: {score_info['streak_count']}天
累计口语练习: {history.get('total_sentences', 0)}句

引导 Mickey 大声朗读英语句子，每读对一句给予积极鼓励。
家长在完成后告诉我完成了几句，我来加分。

评价标准：
- 优秀（+5分/句）：发音准确、流利
- 良好（+5分/句）：基本正确
- 需要改进（+3分/句）：有错误但尝试了
"""
    return prefix


if __name__ == "__main__":
    # 测试
    print("=== 口语练习模块测试 ===")
    for diff in ["基础", "中级", "进阶"]:
        print(f"\n{diff}难度:")
        print(f"  句子: {get_sentence(diff)}")
        challenge = get_daily_challenge(diff)
        print(f"  挑战前100字: {challenge[:100]}...")
    print("\n状态:", get_ongoing_challenge())
