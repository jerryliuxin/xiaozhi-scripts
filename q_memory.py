"""问题记忆模块 — 记住米奇问过的问题

小智每次对话冷启动时会忘记米奇之前问过什么。
这个模块把米奇的问题持久化存储，下次对话时自动注入到 prompt 中，
让 AI 能接着上次的话题继续。"""

import json
import os
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
Q_MEMORY_FILE = os.path.join(BASE_DIR, "question_memory.json")

# 上次回答的缓存（持久化到磁盘）
def _load():
    if os.path.exists(Q_MEMORY_FILE):
        try:
            with open(Q_MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {
        "questions": [],  # 最近30天的问题
        "last_question": None,
        "last_answer": None,
        "last_topic": None,
        "last_date": None,
    }

def _save(data):
    """保存数据（原子写入）。"""
    try:
        tmp_file = Q_MEMORY_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, Q_MEMORY_FILE)
    except Exception:
        pass


def record_question(question, answer, topic=None):
    """记录米奇的问题和AI的回答。"""
    data = _load()
    today = date.today().isoformat()
    now = datetime.now().strftime("%H:%M")

    entry = {
        "question": question[:200],  # 限制长度
        "answer": answer[:500],     # 回答也限制长度
        "topic": topic or "unknown",
        "date": today,
        "time": now,
    }

    data["questions"].append(entry)
    data["last_question"] = question[:200]
    data["last_answer"] = answer[:500]
    data["last_topic"] = topic or "unknown"
    data["last_date"] = today

    # 只保留最近30天
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    data["questions"] = [q for q in data["questions"] if q.get("date", "") >= cutoff]

    _save(data)
    return {"recorded": True, "question": question, "topic": entry["topic"]}


def get_prompt_prefix():
    """生成记忆注入的前缀，让AI知道上次聊了什么。"""
    data = _load()
    if not data.get("last_question"):
        return "【记忆信息】米奇是第一次和小智对话，欢迎热情地打招呼！"

    last_q = data.get("last_question", "")
    last_t = data.get("last_topic", "")
    last_d = data.get("last_date", "")
    last_time = ""

    # 找最近的问题
    recent = data.get("questions", [])[-3:]  # 最近3个问题

    prefix = "【用户个性化信息】\n"
    prefix += f"上次对话主题是 '{last_t}'（{last_d} {last_time}），请接着上次的话题继续。\n\n"

    # 显示最近的问题摘要
    if recent:
        prefix += "最近问过的问题：\n"
        for i, q in enumerate(recent):
            prefix += f"  {i+1}. [{q.get('date', '')}] {q.get('question', '')[:60]}\n"
        prefix += "\n"

    prefix += "[System Instruction for Xiaozhi]\n"
    return prefix


def get_last_topic():
    """获取上次对话主题。"""
    data = _load()
    return {
        "topic": data.get("last_topic"),
        "question": data.get("last_question"),
        "date": data.get("last_date"),
    }


def get_all_history(limit=10):
    """获取问题历史。"""
    data = _load()
    return list(reversed(data.get("questions", [])[-limit:]))


def reset_all():
    """重置问题记忆。"""
    if os.path.exists(Q_MEMORY_FILE):
        os.remove(Q_MEMORY_FILE)
    return True
