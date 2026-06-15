"""用户记忆模块 — 小智个性化记忆系统

持久化存储用户偏好、学习进度、关注股票等，使小智在连续对话中能够记住上下文。
数据存储在 ~/.hermes/xiaozhi_scripts/user_memory.json"""

import json
import os
import sys

MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_memory.json")

def _load():
    """加载用户记忆，返回 dict。文件不存在则返回空 dict。"""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def _save(data):
    """保存用户记忆到 JSON 文件（原子写入）。"""
    try:
        tmp_file = MEMORY_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, MEMORY_FILE)
        return True
    except Exception as e:
        print(f"Memory save error: {e}", file=sys.stderr)
        return False

def get_user_profile():
    """获取用户画像，用于教育对话中个性化调用。"""
    memory = _load()
    return {
        "name": memory.get("name", ""),
        "language_level": memory.get("language_level", "B1"),  # 英语学习等级
        "preferred_topics": memory.get("preferred_topics", []),  # 偏好的对话主题
        "learning_progress": memory.get("learning_progress", {}),
    }

def get_followed_stocks():
    """获取用户关注的股票列表。"""
    memory = _load()
    return memory.get("followed_stocks", [])

def get_last_interaction():
    """获取上次交互信息，用于恢复上下文。"""
    memory = _load()
    return {
        "last_topic": memory.get("last_topic", ""),
        "last_time": memory.get("last_time", ""),
        "last_difficulty": memory.get("last_difficulty", ""),
        "last_text": memory.get("last_text", ""),
    }

def update_interaction(topic, **kwargs):
    """更新最近一次交互信息。"""
    from datetime import datetime
    memory = _load()
    memory["last_topic"] = topic
    memory["last_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    for k, v in kwargs.items():
        memory[f"last_{k}"] = v
    _save(memory)

def update_learning_progress(skill_name, level, score=0):
    """更新学习进度。"""
    memory = _load()
    if "learning_progress" not in memory:
        memory["learning_progress"] = {}
    memory["learning_progress"][skill_name] = {
        "level": level,
        "score": score,
        "updated": memory.get("learning_progress", {}).get(skill_name, {}).get("updated", "unknown")
    }
    from datetime import datetime
    memory["learning_progress"][skill_name]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save(memory)

def set_user_name(name):
    """设置用户姓名。"""
    memory = _load()
    memory["name"] = name
    _save(memory)

def set_language_level(level):
    """设置语言等级 (A1, A2, B1, B2, C1, C2)。"""
    memory = _load()
    memory["language_level"] = level
    _save(memory)

def add_followed_stock(ticker, name=""):
    """添加关注股票。"""
    memory = _load()
    if "followed_stocks" not in memory:
        memory["followed_stocks"] = []
    # 去重
    for item in memory["followed_stocks"]:
        if isinstance(item, dict) and item.get("ticker") == ticker:
            item["name"] = name
            _save(memory)
            return True
    memory["followed_stocks"].append({"ticker": ticker, "name": name})
    _save(memory)
    return True

def remove_followed_stock(ticker):
    """移除关注股票。"""
    memory = _load()
    if "followed_stocks" in memory:
        memory["followed_stocks"] = [
            s for s in memory["followed_stocks"] if s.get("ticker") != ticker
        ]
        _save(memory)
    return True

def get_user_prompt_prefix():
    """生成用户个性化提示词前缀，注入到大模型 prompt 中。"""
    memory = _load()
    parts = []
    
    if memory.get("name"):
        parts.append(f"用户叫{memory['name']}，请用友好的方式称呼ta。")
    
    if memory.get("language_level"):
        ll = memory["language_level"]
        parts.append(f"用户的英语等级是 {ll}，请根据这个水平调整对话难度。")
    
    if memory.get("preferred_topics"):
        topics = ", ".join(memory["preferred_topics"])
        parts.append(f"用户对以下主题特别感兴趣：{topics}，请优先围绕这些话题展开对话。")
    
    # 检查上次交互
    if memory.get("last_topic") and memory.get("last_time"):
        parts.append(f"上次对话主题是 '{memory['last_topic']}'（{memory['last_time']}），请接着上次的话题继续。")
    
    if memory.get("followed_stocks"):
        stocks = [s.get("ticker", s) if isinstance(s, dict) else s for s in memory["followed_stocks"]]
        stock_str = ", ".join(stocks)
        parts.append(f"用户关注以下股票：{stock_str}。如果涉及投资话题，可以结合这些股票进行分析。")
    
    if not parts:
        return ""
    
    nl = "\n"
    return "【用户个性化信息】" + nl + nl.join(parts) + nl + nl

def add_preferred_topic(topic):
    """添加偏好主题。"""
    memory = _load()
    if "preferred_topics" not in memory:
        memory["preferred_topics"] = []
    if topic not in memory["preferred_topics"]:
        memory["preferred_topics"].append(topic)
        _save(memory)
    return True

def reset_memory():
    """重置所有记忆。"""
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
    return True

def memory_to_json():
    """返回完整的记忆数据（用于调试）。"""
    return _load()
