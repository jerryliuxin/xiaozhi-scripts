"""家务追踪模块 — 帮助米奇养成劳动习惯

通过家务获得积分，培养责任感和动手能力。
家长确认完成，AI记录积分。
"""

import random
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
import game_engine

# 家务类型映射
CHORE_TYPES = {
    "整理书桌": "clean_room",
    "整理房间": "clean_room",
    "收拾书桌": "clean_room",
    "洗碗": "dishes",
    "收餐桌": "dishes",
    "倒垃圾": "trash",
    "洗衣服": "laundry",
    "折叠衣服": "laundry",
    "照顾植物": "pets_plants",
    "浇花": "pets_plants",
    "喂宠物": "pets_plants",
}

# 家务鼓励语
CHORE_PHRASES = [
    "米奇真棒！自己的事情自己做，爸爸妈妈为你骄傲！",
    "太厉害了！帮家里分担家务，是个负责任的大孩子了！",
    "哇，干得漂亮！劳动最光荣！+{points}分！",
    "真勤快！会做家务的小朋友最可爱了！",
    "谢谢你帮家里做事！这种精神值得表扬！",
]


def record_chore(chore_name):
    """
    根据家务名称记录积分。
    
    chore_name: 家务名称，如"整理书桌"、"洗碗"、"倒垃圾"
    返回积分结果
    """
    # 映射到标准类型
    chore_type = "other"
    for key, standard in CHORE_TYPES.items():
        if key in chore_name:
            chore_type = standard
            break

    result = game_engine.record_chore(chore_type)
    result["chore_name"] = chore_name
    result["phrase"] = random.choice(CHORE_PHRASES)
    return result


def get_chore_list():
    """获取家务建议列表。"""
    return [
        {"type": "clean_room", "name": "整理书桌/房间", "points": 15, "tips": "把桌面收拾干净，书本分类放好"},
        {"type": "dishes", "name": "帮忙洗碗/收餐桌", "points": 10, "tips": "饭后帮忙把碗筷收到厨房"},
        {"type": "trash", "name": "倒垃圾", "points": 8, "tips": "把家里的垃圾袋拎下楼"},
        {"type": "laundry", "name": "洗衣服/折叠衣服", "points": 12, "tips": "把脏衣服放进洗衣机，洗完帮忙叠"},
        {"type": "pets_plants", "name": "照顾植物/宠物", "points": 5, "tips": "给花浇水、给宠物添粮"},
    ]


def get_prompt_prefix():
    """生成家务激励的前缀。"""
    score_info = game_engine.get_score()
    chore_history = game_engine.get_chore_history(5)
    today_chores = [e for e in chore_history if e.get("date") == str(date.today())]

    prefix = f"""【家务激励模式】
Mickey当前积分: {score_info['total_score']} | 等级: {score_info['level']}
家务总次数: {score_info.get('chore_count', 0)}次
今日家务: {len(today_chores)}次

鼓励米奇参与家务劳动：
1. 主动询问是否需要帮忙
2. 完成家务后给予具体表扬
3. 完成后让家长确认后我来加分

积分规则：整理房间15分，洗碗10分，倒垃圾8分，洗衣服12分，照顾宠物5分
"""
    return prefix


if __name__ == "__main__":
    print("=== 家务追踪模块测试 ===")
    print("家务列表:")
    for item in get_chore_list():
        print(f"  {item['name']}: {item['points']}分")
    print()
    result = record_chore("整理书桌")
    print(f"记录整理书桌: {result}")
