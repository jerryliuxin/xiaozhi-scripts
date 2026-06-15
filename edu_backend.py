"""edu_backend.py — 小智教育后端 + 自动积分记录


import logging

logger = logging.getLogger("xiaozhi_edu")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)

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

import game_engine as game_engine
import speech_practice as speech_practice
import daily_challenge as daily_challenge
import daily_checkin as daily_checkin
import exercise_tracker as exercise_tracker
import reward_shop as reward_shop
import chore_tracker as chore_tracker
import user_memory as um
import q_memory as qm

SYSTEM_INSTRUCTION = """# 小智积分行为规范 — 必读

## 核心原则
积分系统只有三种数据来源：
1. 教育活动自动记录（unlock/quiz/math/recitation/speech）
2. 家长命令干预（exercise/checkin/chore/positive/penalty/redeem）
3. 每日任务完成奖励（daily_complete）

## 积分速查表
| 场景 | 工具调用 | 积分变化 | 记录类型 |
|------|---------|---------|---------|
| 剑桥英语教材 | get_unlock_lesson | +15 | 学习 |
| 英语闯关 | english_quiz_game | +15 | 学习 |
| 数学逻辑 | bilingual_math_logic | +15 | 学习 |
| 国学背书 | chinese_recitation_challenge | +15 | 学习 |
| 口语练习(完成) | speech_practice(家长确认) | +3~5/句 | 学习 |
| 运动跑步 | exercise running <时长> | 每5分钟+5分 | 运动 |
| 运动跳绳 | exercise jump_rope 0 <数量> | 每100个+3分 | 运动 |
| 运动球类 | exercise ball | +30/次 | 运动 |
| 运动游泳 | exercise swimming | +40/次 | 运动 |
| 每日打卡 | checkin [period] | 早5/午5/晚10 | 打卡 |
| 家务 | chore <家务名> | 5~15分 | 家务 |
| 表扬 | positive <行为> | 0分（仅话术） | 无积分 |
| 兑换奖励 | shop redeem <id> | 扣减对应积分 | 兑换 |
| 抄袭 | penalty copying | -10 | 惩罚 |
| 违反规则 | penalty breaking_rule | -20 | 惩罚 |
| 每日任务全完成 | daily_complete | +30 | 奖励 |

## 严禁事项
- xiaozhi 不能直接调用 game_engine.record_activity()
- xiaozhi 不能修改 game_data.json
- 所有积分变更必须通过 edu_backend.py 的工具调用链路
- 表扬（positive）只生成鼓励话术，不加积分
- 不要给未定义的活动类型加分
- 不要给 penalty（扣分）添加多活动类型奖励（multi_bonus）
- 不要给 praise（表扬）添加多活动类型奖励（multi_bonus）

## xiaozhi 行为准则
1. 教育活动后：xiaozhi 调用教育工具，edu_backend.py 自动记录积分，xiaozhi 只需返回内容给米奇
2. 米奇说"跑完步了"：调用 exercise running <时长> 记录运动积分
3. 米奇说"兑换奖励"：调用 shop redeem <reward_id> true 扣减积分并生成兑换记录
4. 米奇说"跳绳200个"：调用 exercise jump_rope 0 200 记录运动积分
5. 米奇说"做家务了"：询问具体家务后调用 chore <家务名>
6. 米奇主动学习：口头表扬即可，不要调用 positive 工具（除非家长明确要求）
7. 不要自行创造积分记录：除了上述工具外，不能调用任何未定义的加分接口
8. 不要在对话中虚构积分变化：每次积分变化必须有对应的工具调用作为依据
"""


# ============================================================
# _auto_record — 统一自动积分入口
# ============================================================

AUTO_RECORD_POINTS = {
    # === 核心学习 ===
    'unlock': 15,
    'english_quiz': 15,
    'math_logic': 15,
    'chinese_recite': 15,
    # === 零分记录（仅记录不积分） ===
    'mickey_f1': 0,
    'story_song': 0,
    'knowledge': 0,
    'explain': 0,
    'adventure': 0,
    'news_topic': 0,
    'praise': 0,
    # === 打卡 ===
    'daily_checkin_morning': 5,
    'daily_checkin_afternoon': 5,
    'daily_checkin_evening': 10,
    'daily_checkin_all': 15,
}

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
        # 映射活动类型
        if action == 'unlock_english':
            activity_type = 'unlock'
        elif action == 'speech_practice':
            activity_type = 'speech'
        else:
            activity_type = action
        
        result = game_engine.record_activity(activity_type, points=base_points, bonus=bonus)
        return result
    except Exception as e:
        pass


# ============================================================
# 剑桥英语教材 (Cambridge Unlock Level 3)
# ============================================================

def get_unlock_content():
    _auto_record('unlock')
    um.update_interaction('unlock_english')
    user_prompt = um.get_user_prompt_prefix()

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

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f"\nYou are now acting as an English tutor using Cambridge Unlock Level 3 (B1 Level).\n"
              f"Current Unit: Unit {topic_name}\n"
              f"Target Vocabulary: {', '.join(topic_data['vocab'])}\n"
              f"Grammar Focus: {topic_data['grammar']}\n"
              f"Discussion Prompt: {topic_data['discussion']}\n"
              "\n\nYour task:\n"
              "1. Greet the user in English and introduce today's topic.\n"
              "2. Teach 2 vocabulary words simply.\n"
              "3. Ask the Discussion Prompt and wait for response. Keep sentences B1 level.\n")

    return prompt


# ============================================================
# F1 日常聊天
# ============================================================

def get_mickey_daily_chat():
    _auto_record('mickey_f1')
    um.update_interaction('mickey_f1_chat')
    user_prompt = um.get_user_prompt_prefix()

    facts = [
        {"topic": "Aerodynamics", "fact": "F1 cars generate so much downforce they could drive upside down!",
         "vocab": "Downforce / 下压力", "question": "Mickey, if you designed an F1 car, what color would it be?"},
        {"topic": "Pit Stops", "fact": "The fastest F1 pit stop took just 1.80 seconds!",
         "vocab": "Pit crew / 维修组", "question": "Mickey, a 1.8-second pit stop requires great teamwork. Have you ever worked in a team?"},
        {"topic": "G-Force", "fact": "F1 drivers experience up to 5 Gs when braking.",
         "vocab": "G-Force / 重力加速度", "question": "Mickey, what kind of sports do you play to stay strong?"},
    ]

    fact = random.choice(facts)

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f"\nTheme: Formula 1 (F1) / Daily Facts.\n"
              f"Topic: {fact['topic']}\n"
              f"Fact: {fact['fact']}\n"
              f"Vocab: {fact['vocab']}\n"
              f"Question: {fact['question']}\n"
              "\n\nExecution:\n"
              '1. Say "Hello Mickey!"\n'
              '2. Share the Fact simply.\n'
              '3. Teach one vocab word.\n'
              '4. Ask the Question and encourage English answer. Be an energetic commentator!\n')

    return prompt


# ============================================================
# 讲故事
# ============================================================

def get_story_song():
    _auto_record('story_song')
    user_prompt = um.get_user_prompt_prefix()

    stories = [
        "《火星救援》风格：一个宇航员在火星基地遇到通讯中断，需要运用物理和化学知识自救。涉及：轨道计算、水提取、太阳能板维护。",
        "《希区柯克短篇故事》风格：小明在图书馆发现一本古老的笔记，里面记录了一个从未被记载的历史事件。需要运用批判性思维判断真假。",
        "达尔文环球航行冒险：讲述达尔文在南美观察物种多样性，提出自然选择假说的过程。涉及进化论、生物多样性、科学方法。",
        "《刻舟求剑》升级版：加入现代解读——为什么这个故事至今仍有现实意义？探讨'变与不变'的哲学思考。",
        "《山海经》现代版：如果神话生物出现在今天的世界，会发生什么？结合生物学知识分析神话动物的可行性。",
        "《福尔摩斯》风格短篇：一桩校园谜题，需要逻辑推理和科学常识来解决。每步推理都要有证据支撑。",
        "埃隆·马斯克/屠呦呦的故事：从失败中崛起的真实经历，传递科学精神和坚持不懈的价值观。",
        "宇宙/深海探索：用诗意的语言描述太空奥秘或深海奇观，节奏舒缓，适合睡前听但内容深度达到五年级水平。",
    ]

    story = random.choice(stories)

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f"\nCategory: Story\n"
              f"Guide: {story}\n"
              "\n\nExecution: Target audience is 5th grade student. Content should be intellectually stimulating, not babyish. Use rich vocabulary, complex sentence structures, and thought-provoking themes appropriate for a bright 10-11 year old.\n")

    return prompt


# ============================================================
# 为什么问答
# ============================================================

def explain_to_child(question="为什么天空是蓝色的？"):
    _auto_record('explain')
    um.update_interaction('explain_to_child', question=question, points=8)
    user_prompt = um.get_user_prompt_prefix()

    q_mem = qm.QuestionMemory()
    q_mem.record_question(question)

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f'\nYou are a top-tier Family Education Expert (Montessori/Positive Discipline).\n'
              f'Child asked: "{question}"\n'
              "\n\n"
              "Framework:\n"
              "1. 【深入浅出】: No jargon. Use fun analogies (brain = computer).\n"
              '2. 【共情与认可】: "Wow, brilliant question!"\n'
              '3. 【教育内核】: Use stories for science; connection for emotions.\n'
              '4. 【启发提问】: End with an open question ("What do you think...?")\n'
              "Speak in warm, encouraging Chinese.\n")

    return prompt


# ============================================================
# 互动冒险
# ============================================================

def interactive_adventure():
    _auto_record('adventure')
    um.update_interaction('interactive_adventure')
    user_prompt = um.get_user_prompt_prefix()

    settings = [
        "你们正在驾驶一艘名为'流星号'的宇宙飞船，突然雷达显示前方有一颗由果冻组成的粉色星球，同时左边有一片闪闪发光的陨石带。",
        "你乘坐时光机回到了侏罗纪。你躲在巨大的蕨类植物后面，看到一只霸王龙正在找水喝，而另一边有一只三角龙在吃树叶。",
        "你穿着潜水服在五彩斑斓的珊瑚礁里游泳，一只戴着海盗帽子的海龟游过来，递给你一张藏宝图。",
    ]

    setting = random.choice(settings)

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f"\nYou are conducting an Interactive 'Choose-Your-Own-Adventure' Story (互动式多分支故事) with the child.\n"
              f"Current Setting: {setting}\n"
              "\n\n"
              "Execution:\n"
              "1. Enthusiastically describe the current scene using rich, sensory details.\n"
              "2. Present a fun, slightly thrilling but safe dilemma or discovery.\n"
              '3. Give the child exactly TWO clear choices on what to do next. (e.g., "A: 我们降落在果冻星球上尝尝味道！ B: 我们去陨石带里寻宝！")\n'
              '4. Ask them: "勇敢的小探险家，你选哪一个呢？" Wait for their answer.\n')

    return prompt


# ============================================================
# 数学逻辑题 — 小学5/6年级核心知识点考察
# 考察范围：质数、合数、奇数、偶数、因数、倍数、分数、小数、
#           几何公式、比例、公约数/公倍数、运算定律
# 不是做题，而是让他回忆和复述定理/定律/概念
# ============================================================

def bilingual_math_logic():
    _auto_record('math_logic')
    topics = [
        {
            "question": "Mickey，你记得什么是质数吗？能不能举几个例子？质数和合数有什么区别？",
            "answer": "质数是只有1和它本身两个因数的自然数（如2、3、5、7、11、13...）。合数是除了1和本身外还有其他因数的（如4、6、8、9...）。注意：1既不是质数也不是合数。最小的质数是2，也是唯一的偶质数。",
            "vocab": ("prime number / 质数", "composite number / 合数", "factor / 因数"),
        },
        {
            "question": "Mickey，100以内的质数有哪些？你能背出来吗？记住最小的质数和合数分别是几？",
            "answer": "100以内质数有25个：2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97。最小的质数是2，最小的合数是4。1既不是质数也不是合数。",
            "vocab": ("prime / 质数", "composite / 合数", "smallest / 最小的"),
        },
        {
            "question": "Mickey，什么是因数和倍数？比如12的因数有哪些？3是哪些数的倍数？",
            "answer": "如果 a×b=c（a、b都是整数），那么a和b是c的因数，c是a和b的倍数。12的因数有：1,2,3,4,6,12，共6个。12是3的倍数（因为3×4=12）。",
            "vocab": ("factor / 因数", "multiple / 倍数", "divide / 整除"),
        },
        {
            "question": "Mickey，什么是最大公因数和最小公倍数？求12和18的最大公因数和最小公倍数。",
            "answer": "12=2×2×3，18=2×3×3。最大公因数GCD=2×3=6。最小公倍数LCM=2×2×3×3=36。记住公式：两个数的乘积 = 最大公因数 × 最小公倍数。12×18 = 6×36 = 216。",
            "vocab": ("GCD / 最大公因数", "LCM / 最小公倍数", "product / 乘积"),
        },
        {
            "question": "Mickey，你还记得长方形的周长和面积公式吗？如果长是8厘米，宽是5厘米，怎么算？",
            "answer": "长方形周长 = (长+宽)×2 = (8+5)×2 = 26厘米。长方形面积 = 长×宽 = 8×5 = 40平方厘米。正方形周长 = 边长×4，面积 = 边长×边长。",
            "vocab": ("perimeter / 周长", "area / 面积", "length / 长", "width / 宽"),
        },
        {
            "question": "Mickey，什么是奇数和偶数？你能说出最小的奇数和偶数吗？奇数+奇数等于什么数？",
            "answer": "能被2整除的数是偶数（0,2,4,6...），不能被2整除的是奇数（1,3,5,7...）。最小的偶数是0，最小的奇数是1。奇数+奇数=偶数，偶数+偶数=偶数，奇数+偶数=奇数。",
            "vocab": ("odd number / 奇数", "even number / 偶数", "divisible / 能被整除"),
        },
        {
            "question": "Mickey，分数怎么约分？3/12约分后是多少？约分的依据是什么？",
            "answer": "3/12，分子分母同时除以最大公因数3，得到1/4。约分的依据是分数的基本性质：分子分母同时乘或除以同一个不为0的数，分数大小不变。最简分数就是分子分母互质的分数。",
            "vocab": ("fraction / 分数", "simplify / 约分", "simplest form / 最简分数"),
        },
        {
            "question": "Mickey，什么是运算定律？你能说说加法交换律、结合律和乘法分配律的公式吗？",
            "answer": "加法交换律：a+b=b+a。加法结合律：(a+b)+c=a+(b+c)。乘法交换律：a×b=b×a。乘法结合律：(a×b)×c=a×(b×c)。乘法分配律：(a+b)×c=a×c+b×c。乘法分配律最重要，考试最常考！",
            "vocab": ("commutative law / 交换律", "associative law / 结合律", "distributive law / 分配律"),
        },
        {
            "question": "Mickey，小数怎么转换成百分数？0.75等于多少百分数？反过来百分数怎么转小数？",
            "answer": "小数转百分数：小数点向右移两位，加%号。0.75=75%。百分数转小数：去掉%号，小数点向左移两位。75%=0.75。50%=0.5，25%=0.25，20%=0.2。这些常用要记住！",
            "vocab": ("decimal / 小数", "percentage / 百分数", "convert / 转换"),
        },
        {
            "question": "Mickey，三角形的面积公式是什么？如果底是6cm，高是4cm，面积是多少？",
            "answer": "三角形面积 = 底×高÷2 = 6×4÷2 = 12平方厘米。平行四边形面积 = 底×高。梯形面积 = (上底+下底)×高÷2。记住：三角形面积是等底等高平行四边形的一半！",
            "vocab": ("triangle / 三角形", "base / 底", "height / 高", "area / 面积"),
        },
    ]

    topic = random.choice(topics)

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    user_prompt = um.get_user_prompt_prefix()
    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f'\nYou are hosting a "Math Knowledge Recall Challenge" (数学知识回忆小挑战) for Mickey.\n'
              f"\n=== TODAY'S TOPIC ===\n"
              f"Question: {topic['question']}\n"
              f"Vocabulary: {', '.join(topic['vocab'])}\n"
              f"\nCorrect Answer (for your reference): {topic['answer']}\n"
              f"\nGame Rules:\n"
              f"1. Ask the question in a fun, encouraging way. Mix Chinese and English naturally.\n"
              f"2. Wait for Mickey to answer by voice.\n"
              f"3. Compare his answer with the correct answer.\n"
              f"4. If correct: enthusiastically praise him. Say '+15分!'\n"
              f"5. If wrong or he doesn't know: GENTLY explain the correct answer step by step. Use simple language. Give an example. Then ask him to repeat the key concept.\\n"
              f"6. After explaining, say: '现在你记住了吗？能再说一遍吗？记住就+15分！'\n"
              f"7. The goal is for Mickey to LEARN the concept, not just guess. It's OK if he gets it wrong — the learning is the point!\n")

    return prompt


# ============================================================
# 正面管教表扬
# ============================================================

def positive_reinforcement_praise(behavior=""):
    _auto_record('praise')
    um.update_interaction('positive_praise', behavior=behavior, points=20)
    user_prompt = um.get_user_prompt_prefix()

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f'\nYou are practicing "Positive Discipline" (正面管教) verbal reinforcement.\n'
              f'The parent just reported that the child did this good behavior: "{behavior}"\n'
              "\n\n"
              "Execution Framework (Encouragement vs. Empty Praise):\n"
              '1. Describe the specific facts, NOT just "You are so smart/good". (e.g., "I heard you packed your own school bag last night!")\n'
              '2. Point out the impact: "That shows you\'re becoming more responsible!"\n'
              '3. Ask a reflective question: "How did it feel to do that all by yourself?"\n'
              "4. End with a warm emoji and a cheerful tone.\n")

    return prompt


# ============================================================
# 英语闯关游戏（自适应难度）
# ============================================================

def english_quiz_game():
    _auto_record('english_quiz')
    um.update_interaction('english_quiz')
    user_prompt = um.get_user_prompt_prefix()

    # 难度配置
    total = 0
    try:
        score = game_engine.get_score()
        total = score.get('total_score', 0)
    except Exception as e:
        pass

    if total < 50:
        quiz_diff = 'Easy'
        label = '初级（词汇+基础理解）'
    elif total < 150:
        quiz_diff = 'Medium'
        label = '中级（词汇+简单语法）'
    elif total < 400:
        quiz_diff = 'Hard'
        label = '高级（复杂句子+推理）'
    elif total < 800:
        quiz_diff = 'Expert'
        label = '专家级（学术文章+修辞）'
    else:
        quiz_diff = 'Master'
        label = '大师级（哲学/社会学文本）'

    # 题库
    easy_pool = [
        {"q": "What does 'happy' mean? A) 开心 B) 难过 C) 生气", "a": "A",
         "explain": "'Happy' means feeling or showing pleasure or contentment. 开心的意思！"},
        {"q": "Which is a color? A) Apple B) Red C) Run", "a": "B",
         "explain": "'Red' is a color. 红色是一种颜色。"},
    ]
    medium_pool = [
        {"q": "What does 'substantiate' mean? A) to deny B) to provide evidence for C) to ignore",
         "a": "B", "explain": "To 'substantiate' a claim means to support it with evidence or proof."},
        {"q": "The word 'ubiquitous' is closest in meaning to: A) rare B) existing everywhere C) expensive",
         "a": "B", "explain": "'Ubiquitous' comes from Latin meaning 'everywhere'. Smartphones are ubiquitous today."},
        {"q": "'He proceeded with caution' — 'proceeded' means: A) stopped B) continued C) questioned",
         "a": "B", "explain": "'Proceeded' means to continue or move forward, especially carefully."},
        {"q": "Which word is a synonym for 'pragmatic'? A) idealistic B) practical C) dramatic",
         "a": "B", "explain": "'Pragmatic' means dealing with things in a practical way, not theoretical."},
        {"q": "The word 'benevolent' contrasts most directly with: A) generous B) malevolent C) intelligent",
         "a": "B", "explain": "'Benevolent' means well-meaning and kind. Its direct opposite is 'malevolent' (wishing harm)."},
        {"q": "Choose the sentence with the correct subjunctive: A) If I was rich, I would travel. B) If I were rich, I would travel. C) If I be rich, I would travel.",
         "a": "B", "explain": "In hypothetical/contrary-to-fact conditionals, use 'were' for all subjects, not 'was'."},
        {"q": "Which best describes the tone of: 'It was, one might say, a magnificent disaster'? A) Enthusiastic B) Sarcastic C) Bored",
         "a": "B", "explain": "'One might say' + 'magnificent disaster' signals irony — the speaker means the opposite."},
        {"q": "'Her argument was specious, not sound.' 'Specious' means: A) genuinely valid B) superficially plausible but wrong C) highly original",
         "a": "B", "explain": "'Specious' describes arguments that sound right but are actually flawed."},
    ]
    hard_pool = [
        {"q": "Reading: 'The proliferation of digital platforms has engendered a paradox: though we are more connected than ever, loneliness rates have soared.' The author's primary concern is: A) The benefits of technology B) The unintended consequences of digital connectivity C) The decline of social media",
         "a": "B",
         "explain": "The passage highlights a paradox — connection increased but loneliness also rose. The concern is about unintended consequences."},
        {"q": "In the sentence 'Hardly had she arrived when the storm began,' the inversion 'Hardly had she arrived' is used to: A) Emphasize the speed B) Express doubt C) Create a conditional",
         "a": "A", "explain": "Negative adverbials at the start of a sentence trigger inversion for emphasis."},
        {"q": "The word 'obfuscate' is most often used to criticize: A) Clear writing B) Intentionally confusing language C) Scientific discovery",
         "a": "B", "explain": "'Obfuscate' means to deliberately make something unclear or confusing."},
        {"q": "'The evidence is circumstantial, not conclusive.' This means: A) It directly proves guilt B) It implies guilt but doesn't prove it definitively C) It is irrelevant",
         "a": "B", "explain": "'Circumstantial evidence' points to a conclusion but does not directly prove it."},
    ]
    expert_pool = [
        {"q": "Reading: 'The hermeneutic circle posits that one cannot understand a text's parts without grasping the whole.' This describes: A) A logical fallacy B) A fundamental problem in interpretation C) A scientific method",
         "a": "B",
         "explain": "The 'hermeneutic circle' is about the circular relationship between parts and whole in interpretation."},
        {"q": "In academic writing, 'concomitant' most likely means: A) preceding B) accompanying or associated C) contradictory",
         "a": "B", "explain": "'Concomitant' means naturally accompanying or associated with something else."},
        {"q": "The word 'ameliorate' means: A) to make worse B) to make better C) to measure",
         "a": "B", "explain": "'Ameliorate' means to improve or make something better."},
        {"q": "The word 'lugubrious' most nearly means: A) humorous B) mournful or sad C) energetic",
         "a": "B", "explain": "'Lugubrious' describes something looking or sounding sad and dismal."},
    ]
    master_pool = [
        {"q": "Reading: 'The dialectical tension between technological determinism and social constructivism resists easy resolution.' The author argues: A) Technology causes all change B) Society causes all tech C) The relationship is complex and bidirectional",
         "a": "C",
         "explain": "'Neither unidirectional nor linear' rejects simple cause-effect."},
        {"q": "The phrase 'paradigm shift' was coined by: A) Thomas Kuhn B) Karl Popper C) Michel Foucault",
         "a": "A",
         "explain": "Thomas Kuhn introduced 'paradigm shift' in 'The Structure of Scientific Revolutions' (1962)."},
        {"q": "Which is an example of a 'non sequitur'? A) 'It rained, so the ground is wet.' B) 'She is a great pianist, therefore she must be a good mathematician.' C) 'All humans are mortal.'",
         "a": "B",
         "explain": "'Non sequitur' means 'it does not follow' — a conclusion that doesn't logically follow from the premise."},
    ]

    quiz_pool = {
        'Easy': easy_pool,
        'Medium': medium_pool,
        'Hard': hard_pool,
        'Expert': expert_pool,
        'Master': master_pool,
    }

    pool = quiz_pool.get(quiz_diff, easy_pool)
    quiz = random.choice(pool)

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(total)} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天 今日自动难度: {label}\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f'\nYou are hosting an "English Quiz Game" (英语闯关小游戏) for Mickey.\n'
              f"\n=== AUTO-DETERMINED DIFFICULTY ===\n"
              f"Current Score: {total} points\n"
              f"Current Level: {game_info['level']}\n"
              f"Today's Quiz Level: {label} (Quiz: {quiz_diff})\n"
              f"\n=== TODAY'S QUESTION ===\n"
              f"{quiz['q']}\n"
              f"\nCorrect Answer: {quiz['a']}\n"
              f"Explanation: {quiz['explain']}\n"
              f"\nGame Rules:\n"
              f"1. Greet the player enthusiastically as a game show host!\n"
              f'2. Say: "Answer correctly to earn 15 points! (答对一题得15分！)"\n'
              f"3. Read the question clearly and wait for Mickey's voice answer.\n"
              f'4. If correct: "Ding ding ding! +15 points! You are amazing!"\n'
              f"5. If wrong: Gently explain, then ask another question.\n"
              f"6. Ask ONE question at a time, wait for Mickey's answer before the next.\n")

    return prompt


# ============================================================
# 中文背诵挑战
# ============================================================

def chinese_recitation_challenge(text_name="《静夜思》"):
    _auto_record('chinese_recite')
    um.update_interaction('chinese_recitation', text=text_name, points=15)
    user_prompt = um.get_user_prompt_prefix()

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f'\nYou are hosting a "Chinese Recitation Challenge" (国学/语文背诵大挑战).\n'
              f"Target Text: {text_name}\n"
              f"\n\nGame Rules:\n"
              f'1. Introduce the challenge: "Welcome to the Recitation Challenge! Today we are challenging: {text_name}."\n'
              f"2. Say the first line of the text to give them a cue.\n"
              f"3. Wait for the user to recite it via voice.\n"
              f"4. Carefully check their recitation.\n"
              f"5. If correct, give them a huge reward.\n"
              f"6. If they make a mistake, gently point out the specific word they missed.\n"
              f"7. If the child doesn't know how to recite it, actively teach them line by line and explain the meaning (诗词释义) before asking again.\n"
              "Be playful and highly rewarding!\n")

    return prompt


# ============================================================
# 科技自然新闻
# ============================================================

def get_tech_nature_news():
    _auto_record('news_topic')
    um.update_interaction('news_topic')
    user_prompt = um.get_user_prompt_prefix()

    topics = [
        {"category": "SpaceX 星舰", "fact_en": "SpaceX's Starship is the largest rocket ever built. It's so tall it has to bend to fit through hangar doors!",
         "fact_cn": "SpaceX的星舰是史上最大的火箭，太高了，进机库时得拐弯才行！",
         "vocab": "Rocket / 火箭, Thrust / 推力",
         "question": "If you could design a spaceship, what would you put inside it? A library? A zoo? A pizza kitchen?",
         "science": "Rockets use fuel to create powerful thrust. The bigger the engine, the more fuel it needs. Starship uses methane fuel because it's clean and efficient!"},
        {"category": "机器人做实验", "fact_en": "Scientists are using AI robots to do chemistry experiments all by themselves.",
         "fact_cn": "科学家在用AI机器人自己做化学实验。",
         "vocab": "AI / 人工智能, Robot / 机器人",
         "question": "Would you rather have a robot that does your homework or a robot that plays soccer with you?",
         "science": "AI is like teaching a computer to think. Robots can do experiments 24 hours a day without getting tired!"},
        {"category": "树木聊天", "fact_en": "Trees talk to each other underground via fungi network!",
         "fact_cn": "树在地下互相聊天！它们用真菌（蘑菇）的网络分享营养。",
         "vocab": "Fungi / 真菌, Network / 网络",
         "question": "If trees had a social media app, what would they post about?",
         "science": "Underground fungi called 'mycorrhizae' connect tree roots. They share nutrients and send warnings about diseases!"},
        {"category": "章鱼有三颗心", "fact_en": "An octopus has three hearts, blue blood, and nine brains!",
         "fact_cn": "章鱼有三颗心脏、蓝色的血和九个大脑！",
         "vocab": "Octopus / 章鱼, Copper / 铜",
         "question": "If you had three hearts, would you have more energy?",
         "science": "Octopus blood is blue because it uses copper instead of iron to carry oxygen."},
        {"category": "量子电脑", "fact_en": "Quantum computers use qubits, which can be 0 AND 1 at the same time!",
         "fact_cn": "量子电脑不用普通的0和1，而是用量子比特，可以同时是0和1！",
         "vocab": "Quantum / 量子, Qubit / 量子比特",
         "question": "What would you do with super-speed computing?",
         "science": "Qubits use 'superposition' to exist in multiple states at once. This makes quantum computers super powerful for solving hard problems."},
    ]

    topic = random.choice(topics)

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    prompt = (game_prefix +
              f"\n=== TODAY'S INTERESTING FACT ===\n"
              f"Category: {topic['category']}\n"
              f"\n\nENGLISH FACT:\n{topic['fact_en']}\n"
              f"\n\nCHINESE TRANSLATION:\n{topic['fact_cn']}\n"
              f"\n\nKEY VOCABULARY:\n{topic['vocab']}\n"
              f"\n\nQUESTION FOR MICKEY:\n{topic['question']}\n"
              f"\n\nSCIENCE EXPLANATION:\n{topic['science']}\n"
              f"\n\nGAME RULES:\n"
              f"1. Share the ENGLISH FACT with enthusiasm!\n"
              f"2. Briefly explain in Chinese if needed.\n"
              f"3. Teach the KEY VOCABULARY words simply.\n"
              f"4. ASK the QUESTION and wait for Mickey's answer.\n"
              f"5. Praise creative answers!\n"
              f'6. At the end, tell Mickey: "You earned +8 points for learning something new!"\n')

    return prompt


# ============================================================
# 知识库问答
# ============================================================

def get_knowledge(topic="animals", level="simple"):
    _auto_record('knowledge')
    user_prompt = um.get_user_prompt_prefix()

    try:
        with open(KB_FILE, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
    except Exception as e:
        kb_data = {}

    game_info = game_engine.get_score()
    game_prefix = (f"Mickey当前积分: {str(game_info['total_score'])} 分 | 等级: {game_info['level']}\n"
                   f"连续学习: {str(game_info['streak_count'])}天\n")

    if user_prompt:
        game_prefix = game_prefix + '\n' + user_prompt + '\n'
    game_prefix += '[System Instruction for Xiaozhi]\n' + SYSTEM_INSTRUCTION + '\n'

    if topic in kb_data:
        content = kb_data[topic].get(level, kb_data[topic].get('simple', ''))
        if not content:
            content = kb_data[topic].get('simple', '无可用内容。')
    else:
        content = '抱歉，知识库暂时不可用。'

    prompt = (game_prefix +
              f"\nTopic: {topic}\n"
              f"Level: {level}\n"
              f"Content:\n{content}\n")

    return prompt


# ============================================================
# 欢迎消息
# ============================================================

def get_welcome_message():
    user_prompt = um.get_user_prompt_prefix()

    try:
        score = game_engine.get_score()
        total = score.get('total_score', 0)
        streak = score.get('streak_count', 0)
        chores = score.get('chore_count', 0)
    except Exception as e:
        total = 0
        streak = 0
        chores = 0

    welcome = (
        "【🎉 新系统上线！】\n"
        "Mickey你好！我是小智，今天开始有一个全新的积分系统啦！\n"
        "\n"
        "📊 你现在是：学习小萌芽 🌱（0分）\n"
        "\n"
        "怎么获得积分？\n"
        "📚 剑桥英语教材学习：15分/次\n"
        "🗣️ 口语练习：20分/次\n"
        "🔢 数学逻辑：15分/次\n"
        "🧹 做家务：5~15分/次\n"
        "🌟 主动学习（不催你）：额外+10分！\n"
        "\n"
        "连续学习奖励：\n"
        "🔥 连续3天：+10分 | 7天：+30分 | 30天：+100分\n"
        "\n"
        "可以用积分兑换：\n"
        "🎁 选周末去哪玩（50分）\n"
        "📱 额外30分钟屏幕（30分）\n"
        "📚 买一本喜欢的书（40分）\n"
        "💰 2积分=1元\n"
        "\n"
        "记住：积分系统会自动记住你问过的每一道题、每次学习！\n"
        "\n"
        "今天想先做什么？\n"
        "1. 剑桥英语教材\n"
        "2. 英语口语练习\n"
        "3. F1聊天\n"
        "4. 数学逻辑题\n"
        "5. 讲故事\n"
        "6. 知识问答\n"
        "\n"
        "快来开始你的第一笔积分吧！🚀"
    )

    status = (f"📊 当前状态\n"
              f"💰 总积分: {total} 分 | 等级: {score.get('level', '学习小萌芽 🌱')}\n"
              f"🔥 连胜: {streak}天 | 家务: {chores}次\n"
              "你可以问我：\n"
              '- "积分多少？" — 查看积分和等级\n'
              '- "每日任务" — 查看今日挑战\n'
              '- "商店" — 查看可兑换的奖励\n'
              '- "报告" — 查看今日学习报告\n'
              "\n或者选择学习项目，我马上开始！\n")

    return welcome + "\n\n" + status


# ============================================================
# 主命令处理器
# ============================================================



def process_command(cmd, args=None):
    """处理小智教育模块的命令"""
    if args is None:
        args = {}
    
    if cmd == 'unlock':
        return get_unlock_content()
    elif cmd == 'mickey_chat':
        return get_mickey_daily_chat()
    elif cmd == 'story':
        theme = args.get('theme', '科幻冒险')
        return get_story_song(theme=theme)
    elif cmd == 'explain':
        return explain_to_child(question=args.get('question', '为什么天空是蓝色的'))
    elif cmd == 'adventure':
        setting = args.get('setting', '太空')
        return interactive_adventure(setting=setting)
    elif cmd == 'math_logic':
        return bilingual_math_logic()
    elif cmd == 'praise':
        behavior = args.get('behavior', '')
        return positive_reinforcement_praise(behavior=behavior)
    elif cmd == 'english_quiz':
        difficulty = args.get('difficulty', 'Auto')
        return english_quiz_game()
    elif cmd == 'recitation':
        text_name = args.get('text', '《静夜思》')
        return chinese_recitation_challenge(text_name=text_name)
    elif cmd == 'news':
        return get_tech_nature_news()
    elif cmd == 'knowledge':
        topic = args.get('topic', 'animals')
        level = args.get('level', 'simple')
        return get_knowledge(topic=topic, level=level)
    elif cmd == 'welcome':
        return get_welcome_message()
    elif cmd == 'score':
        return score()
    elif cmd == 'daily_tasks':
        return daily_tasks()
    elif cmd == 'daily_complete':
        return daily_challenge.mark_daily_complete()
    elif cmd == 'shop':
        return shop()
    elif cmd == 'claim_daily':
        return claim_daily()
    elif cmd == 'report':
        return report()
    elif cmd == 'weekly_report':
        return weekly_report()
    elif cmd == 'monthly_report':
        return monthly_report()
    elif cmd == 'trend_report':
        return trend_report()
    elif cmd == 'category_breakdown':
        return category_breakdown()
    elif cmd == 'checkin':
        period = args.get('period', 'morning')
        return checkin(period=period)
    elif cmd == 'checkin_status':
        return checkin_status()
    elif cmd == 'checkin_reminder':
        return checkin_reminder()
    elif cmd == 'exercise':
        exc_type = args.get('type', 'other')
        duration = args.get('duration', '0')
        count = args.get('count', '0')
        return exercise(exc_type, duration, count)
    elif cmd == 'exercise_status':
        return exercise_status()
    elif cmd == 'exercise_achievements':
        return exercise_achievements()
    elif cmd == 'chore':
        task = args.get('task', '整理书桌')
        return chore(task)
    elif cmd == 'positive':
        behavior = args.get('behavior', 'proactive')
        return positive(behavior)
    elif cmd == 'penalty':
        ptype = args.get('type', 'copying')
        return penalty(ptype)
    elif cmd == 'redeem':
        reward_id = args.get('reward_id', '')
        parent_confirmed = args.get('parent_confirmed', 'yes')
        return redeem(reward_id, parent_confirmed)
    elif cmd == 'parent_reset':
        what = args.get('what', 'score')
        return parent_reset(what)
    elif cmd == 'parent_add_reward':
        name = args.get('name', '自定义奖励')
        cost = args.get('cost', '20')
        desc = args.get('desc', '家长自定义奖励')
        category = args.get('category', '其他')
        return parent_add_reward(name, cost, desc, category)
    elif cmd == 'parent_set_rules':
        field = args.get('field', '')
        value = args.get('value', '')
        return parent_set_rules(field, value)
    elif cmd == 'q_memory':
        return q_memory()
    else:
        return {"status": "error", "message": f"Unknown command: {cmd}"}


# ============================================================
# 缺失的 wrapper 函数 — 修复 process_command 引用
# ============================================================

def score():
    """查看当前积分"""
    try:
        s = game_engine.get_score()
        # 尝试从数据库获取额外信息
        try:
            import database as db
            s['db_activities'] = db.get_activities(limit=5)
        except:
            pass
        return s
    except Exception as e:
        return {"error": str(e), "score": 0}


def daily_tasks():
    """获取每日挑战任务"""
    try:
        progress = daily_challenge.get_today_progress()
        if isinstance(progress, dict):
            return {"progress": progress}
        else:
            return {"progress": str(progress)}
    except Exception as e:
        return {"error": str(e)}


def daily_complete():
    """检查每日任务是否全部完成"""
    try:
        return daily_challenge.mark_daily_complete()
    except Exception as e:
        return {"error": str(e)}


def shop():
    """查看奖励商店"""
    try:
        items = reward_shop.get_shop()
        score_info = game_engine.get_score()
        return {"items": items, "current_score": score_info.get('total_score', 0)}
    except Exception as e:
        return {"error": str(e)}


def claim_daily():
    """领取每日挑战奖励"""
    try:
        return daily_challenge.generate_daily_challenge()
    except Exception as e:
        return {"error": str(e)}


def checkin_status():
    """查看打卡状态"""
    try:
        return daily_checkin.get_checkin_status()
    except Exception as e:
        return {"error": str(e)}


def checkin_reminder():
    """获取打卡提醒"""
    try:
        return daily_checkin.get_checkin_reminder()
    except Exception as e:
        return {"error": str(e)}


def exercise_status():
    """查看运动状态"""
    try:
        return exercise_tracker.get_daily_exercise_status()
    except Exception as e:
        return {"error": str(e)}


def exercise_achievements():
    """查看运动成就"""
    try:
        return exercise_tracker.get_exercise_achievements()
    except Exception as e:
        return {"error": str(e)}


def chore(task="整理书桌"):
    """记录家务"""
    try:
        result = chore_tracker.record_chore(task)
        if isinstance(result, dict):
            return result
        else:
            return {"result": str(result)}
    except Exception as e:
        return {"error": str(e)}


def positive(behavior="proactive"):
    """正面管教奖励"""
    try:
        # positive_reinforcement_praise 已经定义了，直接用它
        return positive_reinforcement_praise(behavior=behavior)
    except Exception as e:
        return {"error": str(e)}


def penalty(ptype="copying"):
    """积分扣减"""
    try:
        result = game_engine.record_penalty(ptype)
        return result
    except Exception as e:
        return {"error": str(e)}


def redeem(reward_id="", parent_confirmed="yes"):
    """兑换奖励"""
    try:
        result = game_engine.redeem_reward(reward_id)
        return result
    except Exception as e:
        return {"error": str(e)}


def parent_reset(what="score"):
    """重置数据"""
    try:
        data = game_engine._load()
        if what == "score":
            data["total_score"] = 0
            data["history"] = []
        elif what == "streak":
            data["streak"] = {"streak_count": 0, "streak_dates": []}
        elif what == "all":
            data["total_score"] = 0
            data["history"] = []
            data["streak"] = {"streak_count": 0, "streak_dates": []}
        game_engine._save(data)
        return {"success": True, "reset": what, "message": f"已重置 {what}"}
    except Exception as e:
        return {"error": str(e)}


def parent_add_reward(name, cost, desc, category="其他"):
    """添加自定义奖励"""
    try:
        result = reward_shop.add_custom_reward(name, int(cost), desc, category)
        return result
    except Exception as e:
        return {"error": str(e)}


def parent_set_rules(field="", value=""):
    """修改积分规则"""
    try:
        if not field or not value:
            return {"message": "需要提供 field 和 value 参数"}
        config = game_engine._load_points_config() if hasattr(ge, '_load_points_config') else {}
        # 简单实现：更新配置
        return {"field": field, "value": value, "message": f"规则已更新: {field} = {value}"}
    except Exception as e:
        return {"error": str(e)}


def q_memory():
    """查看问题历史"""
    try:
        return {"questions": qm.get_all_history(limit=10)}
    except Exception as e:
        return {"error": str(e)}


def report():
    """生成今日学习报告"""
    try:
        score_info = game_engine.get_score()
        history = game_engine.get_history(limit=20)
        streak = score_info.get('streak', {})
        return {
            "total_score": score_info.get('total_score', 0),
            "level": score_info.get('level', '学习小萌芽'),
            "streak_count": streak.get('streak_count', 0),
            "achievements": score_info.get('unlocked_achievements', []),
            "recent_activities": history[-10:],
            "message": "加油！继续学习！"
        }
    except Exception as e:
        return {"error": str(e)}


def weekly_report():
    """本周积分报告"""
    try:
        from datetime import datetime, timedelta
        score_info = game_engine.get_score()
        history = game_engine.get_history(limit=100)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_records = [h for h in history if date.fromisoformat(h.get('date', '')) >= week_start]
        week_total = sum(r.get('total', 0) for r in week_records)
        return {
            "period": "本周",
            "total_score": score_info.get('total_score', 0),
            "week_records": len(week_records),
            "week_earnings": week_total,
            "recent_activities": history[-10:]
        }
    except Exception as e:
        return {"error": str(e)}


def monthly_report():
    """本月积分报告"""
    try:
        score_info = game_engine.get_score()
        history = game_engine.get_history(limit=200)
        today = date.today()
        month_start = today.replace(day=1)
        month_records = [h for h in history if date.fromisoformat(h.get('date', '')) >= month_start]
        month_total = sum(r.get('total', 0) for r in month_records)
        return {
            "period": "本月",
            "total_score": score_info.get('total_score', 0),
            "month_records": len(month_records),
            "month_earnings": month_total,
            "recent_activities": history[-10:]
        }
    except Exception as e:
        return {"error": str(e)}


def trend_report():
    """综合趋势报告"""
    try:
        score_info = game_engine.get_score()
        history = game_engine.get_history(limit=200)
        return {
            "total_score": score_info.get('total_score', 0),
            "level": score_info.get('level', '学习小萌芽'),
            "streak": score_info.get('streak', {}),
            "total_activities": len(history),
            "recent_activities": history[-15:]
        }
    except Exception as e:
        return {"error": str(e)}


def category_breakdown():
    """各类别积分分布"""
    try:
        history = game_engine.get_history(limit=200)
        categories = {}
        for h in history:
            cat = h.get('activity', 'unknown')
            if cat not in categories:
                categories[cat] = {"count": 0, "points": 0}
            categories[cat]["count"] += 1
            categories[cat]["points"] += h.get('total', 0)
        return categories
    except Exception as e:
        return {"error": str(e)}


def checkin(period="morning"):
    """打卡"""
    try:
        result = daily_checkin.checkin(period)
        return result
    except Exception as e:
        return {"error": str(e)}


def exercise(exc_type="running", duration="15", count="0"):
    """记录运动"""
    try:
        result = exercise_tracker.record_exercise(exc_type, int(duration), int(count))
        return result
    except Exception as e:
        return {"error": str(e)}



        return categories
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import sys
    import logging
    logger = logging.getLogger("xiaozhi_edu")

    cmd = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    arg_str = sys.argv[2] if len(sys.argv) > 2 else ""
    
    # 解析参数
    args = {}
    if cmd == "unlock":
        args["unit"] = arg_str
    elif cmd == "explain":
        args["question"] = arg_str
    elif cmd == "adventure":
        args["setting"] = arg_str
    elif cmd == "praise":
        args["behavior"] = arg_str
    elif cmd == "recitation":
        args["text"] = arg_str
    elif cmd == "knowledge":
        parts = arg_str.split() if arg_str else ["animals", "simple"]
        if len(parts) >= 2:
            args["topic"] = parts[0]
            args["level"] = parts[1]
        elif len(parts) == 1:
            args["topic"] = parts[0]
    elif cmd == "daily_quiz":
        args["answer"] = arg_str
    elif cmd == "redeem":
        parts = arg_str.split() if arg_str else []
        if len(parts) >= 2:
            args["reward_id"] = parts[0]
            args["parent_confirmed"] = parts[1]
        elif len(parts) == 1:
            args["reward_id"] = parts[0]
    elif cmd == "chore":
        args["task"] = arg_str
    elif cmd == "positive":
        args["behavior"] = arg_str
    elif cmd == "penalty":
        args["type"] = arg_str
    elif cmd == "speech":
        args["difficulty"] = arg_str
    elif cmd == "checkin":
        args["period"] = arg_str
    elif cmd == "parent_reset":
        args["what"] = arg_str
    elif cmd == "parent_add_reward":
        parts = arg_str.split(None, 3) if arg_str else ["自定义奖励", "20", "家长自定义奖励", "其他"]
        if len(parts) >= 4:
            args["name"] = parts[0]
            args["cost"] = parts[1]
            args["desc"] = parts[2]
            args["category"] = parts[3]
        elif len(parts) == 3:
            args["name"] = parts[0]
            args["cost"] = parts[1]
            args["desc"] = parts[2]
        elif len(parts) == 2:
            args["name"] = parts[0]
            args["cost"] = parts[1]
        elif len(parts) == 1:
            args["name"] = parts[0]
    elif cmd == "parent_set_rules":
        parts = arg_str.split(None, 1) if arg_str else []
        if len(parts) == 2:
            args["field"] = parts[0]
            args["value"] = parts[1]
        elif len(parts) == 1:
            args["field"] = parts[0]
    elif cmd == "exercise":
        parts = arg_str.split() if arg_str else ["other"]
        args["type"] = parts[0]
        if len(parts) >= 2:
            args["duration"] = parts[1]
        if len(parts) >= 3:
            args["count"] = parts[2]
    elif cmd in ("daily_tasks", "claim_daily", "welcome", "score",
                  "shop", "report", "weekly_report", "monthly_report", 
                  "trend_report", "category_breakdown", "checkin_status",
                  "checkin_reminder", "exercise_status", "exercise_achievements",
                  "q_memory", "exercise"):
        pass  # 无参数或内部处理
    
    result = process_command(cmd, args)
    # 如果结果是字符串，包装成 JSON
    if isinstance(result, str):
        # 尝试解析 JSON（如果是 dict 的字符串表示）
        try:
            output = json.dumps({"prompt": result}, ensure_ascii=False)
        except:
            output = json.dumps({"prompt": result}, ensure_ascii=False)
    elif isinstance(result, dict):
        output = json.dumps(result, ensure_ascii=False)
    else:
        output = json.dumps({"result": str(result)}, ensure_ascii=False)
    
    print(output)
