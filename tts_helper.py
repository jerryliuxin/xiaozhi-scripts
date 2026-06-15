"""TTS 语音朗读模块 — 适合儿童使用的语音反馈

使用 edge-tts（免费）或 macOS 系统自带 say 命令。
"""
import asyncio
import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent

CACHE_DIR = BASE_DIR / "audio_cache"
CACHE_DIR.mkdir(exist_ok=True)

async def text_to_speech(text: str, language: str = "zh-CN", voice: str = "zh-CN-XiaoxiaoNeural") -> str:
    """将文本转为语音，返回音频文件路径。
    
    Args:
        text: 要朗读的文本
        language: 语言代码（zh-CN / en-US）
        voice: 语音模型名称
    
    Returns:
        音频文件路径，失败则返回空字符串
    """
    try:
        import edge_tts
        audio_file = str(CACHE_DIR / f"{hash(text) % 1000000}.mp3")
        
        if os.path.exists(audio_file):
            return audio_file
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(audio_file)
        return audio_file
    except ImportError:
        # edge-tts 未安装，尝试系统命令
        return _system_tts(text, language)

def _system_tts(text: str, language: str = "zh-CN") -> str:
    """使用系统 TTS 命令（macOS say / Windows sapi）。"""
    try:
        audio_file = str(CACHE_DIR / f"{hash(text) % 1000000}.wav")
        
        if os.path.exists(audio_file):
            return audio_file
        
        if os.name == "posix":
            # macOS say 命令
            subprocess.run(["say", "-o", audio_file, "-v", "Ting-Ting", text], 
                          capture_output=True, timeout=30)
        else:
            # Windows 不支持直接 say，返回空
            return ""
        
        return audio_file
    except Exception:
        return ""

def score_tts(total_score: int, level: str) -> str:
    """积分变动时的 TTS 文本。"""
    return f"当前积分 {total_score} 分，等级 {level}。继续保持！"

def checkin_tts(period: str) -> str:
    """打卡完成 TTS。"""
    return f"太棒了！{period}打卡成功！"

def redeem_tts(item_name: str, cost: int) -> str:
    """兑换奖励 TTS。"""
    return f"恭喜兑换 {item_name}！花费 {cost} 分！"

def daily_complete_tts(count: int) -> str:
    """每日任务全完成 TTS。"""
    if count >= 4:
        return "今天太厉害了！全部任务都完成了！"
    elif count >= 2:
        return f"完成了 {count} 个任务，继续加油！"
    return "加油！今天多完成任务哦！"

def praise_tts(message: str) -> str:
    """表扬 TTS。"""
    return f"米奇真棒！{message}"
