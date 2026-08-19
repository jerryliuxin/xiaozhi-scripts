#!/usr/bin/env python3
"""
cloud_score_sync.py — 从小智云端聊天记录同步积分

功能：
- 读取云端所有聊天记录
- 分析对话内容，智能识别以下活动：
  · 英语闯关（≥5分钟英语对话）
  · 语文背书（≥5分钟语文背书）
  · 练习作文（≥5分钟写作）
  · 体育打卡（明确提到运动）
  · 家务打卡（明确提到家务）
  · 每日打卡（早/中/晚）
- 自动补录到 game_data.json
- 记录已同步的 chat_id，避免重复处理

使用：
  python3 cloud_score_sync.py              # 全量同步
  python3 cloud_score_sync.py --full       # 强制重新扫描所有聊天
  python3 cloud_score_sync.py --chat 12345 # 只同步指定聊天
  python3 cloud_score_sync.py --dry-run    # 预览不写入
"""

import os
import sys
import json
import re
import time
import requests
from datetime import datetime, timedelta, date

# ── 配置 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.path.join(BASE_DIR, ".cloud_auth.env")
GAME_DATA = os.path.join(BASE_DIR, "game_data.json")
SYNC_LOG = os.path.join(BASE_DIR, ".cloud_sync_log.json")
ENGLISH_KEYWORDS = ['英语', 'English', '口语', 'english', '背书', '背诵', 'recite', '背课文', '练习', 'speaking']
EXERCISE_KEYWORDS = ['跑步', '运动', '跳绳', '游泳', '打球', '跑步', 'exercise', 'run', 'sport', '晨跑']
CHORE_KEYWORDS = ['家务', '洗碗', '扫地', '拖地', '整理', '做饭', '洗衣', 'chore', 'clean', 'dishes']
CHECKIN_KEYWORDS = ['打卡', '签到', 'checkin', 'check in']
RECITE_KEYWORDS = ['背诵', '背书', '朗诵', '古文', '古诗', '诗词', 'recite', 'recitation']
COMPOSITION_KEYWORDS = ['作文', '写作', '写文章', 'essay', 'composition', '写日记']

# 活动配置（与 SESSION_CONFIG 和 LEARNING_POINTS 一致）
ACTIVITY_CONFIG = {
    'english_quiz':  {'keywords': ENGLISH_KEYWORDS, 'min_minutes': 5, 'max_per_day': 2, 'points': 15, 'label': '英语闯关'},
    'chinese_recite':{'keywords': RECITE_KEYWORDS,  'min_minutes': 5, 'max_per_day': 2, 'points': 15, 'label': '语文背书'},
    'composition':   {'keywords': COMPOSITION_KEYWORDS, 'min_minutes': 5, 'max_per_day': 2, 'points': 15, 'label': '练习作文'},
    'exercise':      {'keywords': EXERCISE_KEYWORDS, 'min_minutes': 0, 'max_per_day': 3, 'points': 15, 'label': '体育打卡'},
    'chore':         {'keywords': CHORE_KEYWORDS,    'min_minutes': 0, 'max_per_day': 2, 'points': 15, 'label': '家务打卡'},
}

# 排除关键词（包含这些的聊天不计分）
EXCLUDE_TITLES = ['米花', '测试', '测试', '点歌', '儿歌', '故事', '音乐', '退下', '拜拜',
                   '晚安', '家庭', '天气', '价格', '股票', '茅台', '股价', '查询',
                   '儿歌', '电话', '照明', '灯光', '开关', '音量']
EXCLUDE_SUMMARIES = ['米花', '妹妹', '点歌', '股票', '茅台', '查询', '价格', '股价',
                      '儿歌', '故事', '童话', '唱歌', '晚安', '退下']

# 哪些活动的判定需要检查聊天内容（不仅仅是标题摘要）
NEED_CONTENT_CHECK = ['exercise', 'chore', 'composition', 'chinese_recite', 'checkin']

# ── 工具函数 ──────────────────────────────────────────

def load_auth():
    """加载云端认证信息。"""
    if not os.path.exists(AUTH_FILE):
        print(f"❌ 未找到认证文件: {AUTH_FILE}")
        print("   请从控制台获取 token 后写入")
        sys.exit(1)
    
    auth = {}
    with open(AUTH_FILE) as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                auth[k.strip()] = v.strip().strip('"').strip("'")
    
    return auth


def get_session(auth):
    """创建带认证的 requests session。"""
    s = requests.Session()
    s.headers.update({
        'Authorization': f"Bearer {auth['CLOUD_TOKEN']}",
        'Cookie': auth['CLOUD_COOKIE'],
        'User-Agent': 'Mozilla/5.0',
    })
    return s


def fetch_all_chats(session, base_url, page_size=100):
    """获取所有聊天记录。"""
    all_chats = []
    page = 1
    while True:
        try:
            r = session.get(
                f"{base_url}/api/chats/list",
                params={'page': page, 'pageSize': page_size},
                timeout=15
            )
            if r.status_code != 200:
                print(f"⚠️  获取聊天列表失败: {r.status_code}")
                break
            data = r.json()
            if not data.get('success'):
                print(f"⚠️  API 返回失败: {data}")
                break
            chats = data['data']['list']
            if not chats:
                break
            all_chats.extend(chats)
            if len(chats) < page_size:
                break
            page += 1
        except Exception as e:
            print(f"⚠️  请求异常: {e}")
            if len(all_chats) == 0:
                _retry_fetch_all(session, base_url, page_size, all_chats, e)
            break
    
    return all_chats


def _retry_fetch_all(session, base_url, page_size, all_chats, first_err, attempts=3):
    """对瞬时网络/SSL 故障做退避重试, 避免一次抖动把在线数据误判为 0 条。"""
    for i in range(1, attempts + 1):
        time.sleep(2 * i)
        try:
            r = session.get(
                f"{base_url}/api/chats/list",
                params={'page': 1, 'pageSize': page_size},
                timeout=15
            )
            if r.status_code == 200:
                data = r.json()
                chats = data.get('data', {}).get('list') or []
                all_chats.extend(chats)
                print(f"🔁 重试第 {i} 次成功, 拉取到 {len(chats)} 条聊天")
                return
            print(f"🔁 重试第 {i} 次, 状态码 {r.status_code}")
        except Exception as e:
            print(f"🔁 重试第 {i} 次异常: {e}")
    print(f"❌ 网络重试 {attempts} 次仍失败, 首次异常: {first_err}")


def fetch_chat_messages(session, base_url, chat_id, max_pages=5):
    """获取指定聊天的所有消息。"""
    all_msgs = []
    for page in range(1, max_pages + 1):
        try:
            r = session.get(
                f"{base_url}/api/chats/messages",
                params={
                    'chatId': chat_id,
                    'page': page,
                    'pageSize': 50,
                    'includeTools': 1,
                    'order': 'asc'
                },
                timeout=10
            )
            if r.status_code != 200:
                break
            data = r.json()
            msgs = data['data']['list']
            if not msgs:
                break
            all_msgs.extend(msgs)
            if len(msgs) < 50:
                break
        except:
            break
    return all_msgs


def utc_to_beijing(utc_str):
    """UTC 时间转北京时间。"""
    utc = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
    return utc + timedelta(hours=8)


def load_game_data():
    """加载本地积分数据。"""
    with open(GAME_DATA) as f:
        return json.load(f)


def save_game_data(data):
    """保存积分数据（原子写入）。"""
    tmp = GAME_DATA + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, GAME_DATA)


def load_sync_log():
    """加载同步日志。"""
    if os.path.exists(SYNC_LOG):
        try:
            with open(SYNC_LOG) as f:
                return json.load(f)
        except:
            pass
    return {"synced_chats": [], "last_sync": None}


def save_sync_log(log):
    """保存同步日志。"""
    log['last_sync'] = datetime.now().isoformat()
    with open(SYNC_LOG, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def has_activity_on_date(data, date_str, activity):
    """检查指定日期是否已有该活动记录。"""
    count = 0
    for e in data.get('history', []):
        if e.get('date') == date_str and e.get('activity') == activity:
            count += 1
    return count


def add_activity_record(data, date_str, activity, points, label, source='cloud_sync'):
    """添加一条活动记录到 game_data。"""
    if 'history' not in data:
        data['history'] = []
    
    new_entry = {
        'date': date_str,
        'activity': activity,
        'total': points,
        'label': label,
        'source': source,
        'points': points,
        'bonus': 0,
    }
    data['history'].append(new_entry)
    data['total_score'] = data.get('total_score', 0) + points
    return new_entry


def classify_chat_by_summary(title, summary, duration_min, msg_count):
    """
    根据聊天标题和摘要初步判断活动类型。
    返回可能的活动列表。
    """
    text = (title + ' ' + summary).lower()
    candidates = []
    
    for activity, cfg in ACTIVITY_CONFIG.items():
        # 检查关键词
        for kw in cfg['keywords']:
            if kw.lower() in text:
                if duration_min >= cfg['min_minutes']:
                    candidates.append({
                        'activity': activity,
                        'confidence': 'summary',
                        'duration_min': duration_min,
                    })
                break
    
    return candidates


def classify_chat_by_messages(msgs, duration_min):
    """
    根据聊天消息内容更精确地判断活动。
    """
    if not msgs:
        return []
    
    # 收集所有用户消息
    user_texts = []
    assistant_texts = []
    tool_calls = []
    
    for msg in msgs:
        content = msg.get('content', '')
        role = msg.get('role', '')
        if role == 'user':
            user_texts.append(content)
        elif role == 'assistant':
            assistant_texts.append(content)
        elif role == 'tool':
            try:
                tc = json.loads(content)
                if isinstance(tc, list):
                    for t in tc:
                        tool_calls.append(t.get('name', ''))
            except:
                pass
    
    all_user = ' '.join(user_texts).lower()
    all_text = ' '.join(user_texts + assistant_texts).lower()
    
    results = []
    
    # 检测英语闯关：用户说英语比重高 + 持续时间≥5分钟
    if duration_min >= 5:
        eng_chars = sum(1 for c in all_user if c.isascii() and c.isalpha())
        total_chars = len(all_user.strip())
        eng_ratio = eng_chars / max(total_chars, 1)
        
        # 同时检查小智的回复是否包含英文教学
        has_english_teaching = any(k in all_text for k in [
            'pronunciation', 'grammar', 'correct', '英语', '发音', '语法',
            'try again', 'read after', '背诵', 'recite'
        ])
        
        if eng_ratio > 0.15 or has_english_teaching:
            results.append({
                'activity': 'english_quiz',
                'confidence': 'content',
                'evidence': f'eng_ratio={eng_ratio:.2f}',
                'duration_min': duration_min,
            })
    
    # 检测语文背书
    recite_kw = ['背诵', '背书', '朗诵', '古文', '古诗', '诗词']
    if any(k in all_user for k in recite_kw) and duration_min >= 5:
        results.append({
            'activity': 'chinese_recite',
            'confidence': 'content',
            'evidence': 'recite keywords found',
            'duration_min': duration_min,
        })
    
    # 检测作文
    comp_kw = ['作文', '写作', '写文章', 'essay', '写日记', 'composition']
    if any(k in all_user for k in comp_kw) and duration_min >= 5:
        results.append({
            'activity': 'composition',
            'confidence': 'content',
            'evidence': 'composition keywords found',
            'duration_min': duration_min,
        })
    
    # 检测运动（需要用户明确说）
    exercise_kw = ['跑步了', '运动了', '跳绳了', '游泳了', '打球了', '跑了步']
    if any(k in all_user for k in exercise_kw):
        results.append({
            'activity': 'exercise',
            'confidence': 'content',
            'evidence': 'exercise claim found',
            'duration_min': duration_min,
        })
    
    # 检测家务（需要用户明确说）
    chore_kw = ['洗碗了', '扫了地', '拖了地', '做了家务', '整理了房间', '洗了衣服']
    if any(k in all_user for k in chore_kw):
        results.append({
            'activity': 'chore',
            'confidence': 'content',
            'evidence': 'chore claim found',
            'duration_min': duration_min,
        })
    
    # 检测打卡意图
    checkin_kw = ['打卡', '签到', 'checkin', '早打卡', '晚打卡']
    if any(k in all_user for k in checkin_kw):
        results.append({
            'activity': 'checkin',
            'confidence': 'content',
            'evidence': 'checkin keyword found',
            'duration_min': duration_min,
        })
    
    return results


# ── 主同步逻辑 ────────────────────────────────────────

def sync(dry_run=False, force_full=False, single_chat=None):
    """执行同步。"""
    auth = load_auth()
    session = get_session(auth)
    base = auth.get('CLOUD_BASE', 'https://xiaozhi.me')
    
    game_data = load_game_data()
    sync_log = load_sync_log()
    synced_ids = set(sync_log.get('synced_chats', []))
    
    # 获取所有聊天
    print("📡 获取云端聊天列表...")
    all_chats = fetch_all_chats(session, base)
    print(f"   共 {len(all_chats)} 条聊天记录\n")
    
    # 筛选需要处理的聊天
    if single_chat:
        all_chats = [c for c in all_chats if c['id'] == single_chat]
        if not all_chats:
            print(f"❌ 未找到聊天 {single_chat}")
            return
    
    if not force_full:
        all_chats = [c for c in all_chats if str(c['id']) not in synced_ids]
        if not all_chats:
            print("✅ 所有聊天已同步，无需更新")
            return
    
    stats = {'scanned': 0, 'added': 0, 'skipped': 0, 'errors': 0}
    
    for chat in all_chats:
        chat_id = chat['id']
        created = chat['created_at'][:19]
        bj = utc_to_beijing(created)
        date_str = bj.strftime('%Y-%m-%d')
        duration_min = chat.get('duration', 0) // 60
        title = (chat.get('chat_summary') or {}).get('title', '')
        summary = (chat.get('chat_summary') or {}).get('summary', '')
        msg_count = chat.get('msg_count', 0)
        
        # 跳过今天的聊天（由本地自动记录）
        if date_str == date.today().isoformat():
            continue
        
        # 跳过已知的非学习类聊天（米花、股票、音乐等）
        title_lower = title.lower()
        summary_lower = summary.lower()
        is_excluded = any(kw.lower() in title_lower for kw in EXCLUDE_TITLES) or any(kw.lower() in summary_lower for kw in EXCLUDE_SUMMARIES)
        if is_excluded:
            continue
        
        # 跳过过短的聊天（<5分钟且不是运动/家务）
        if duration_min < 5:
            continue
        
        stats['scanned'] += 1
        time_str = bj.strftime('%H:%M')
        
        # 先根据标题摘要判断
        candidates = classify_chat_by_summary(title, summary, duration_min, msg_count)
        
        # 如果摘要判断有结果，再下载消息内容确认
        if candidates:
            print(f"  🔍 Chat {chat_id} [{date_str} {time_str}] {title[:40]}...")
            msgs = fetch_chat_messages(session, base, chat_id)
            detailed = classify_chat_by_messages(msgs, duration_min)
            
            if detailed:
                candidates = detailed
            
            for cand in candidates:
                act = cand['activity']
                cfg = ACTIVITY_CONFIG.get(act)
                if not cfg:
                    continue
                
                # 检查是否已记录（优先用 SQLite）
                try:
                    from database import get_daily_count
                    existing_count = get_daily_count(date_str, act)
                except ImportError:
                    existing_count = has_activity_on_date(game_data, date_str, act)
                if existing_count >= cfg['max_per_day']:
                    print(f"    ⏭️  {act} 已达每日上限 ({existing_count}/{cfg['max_per_day']})")
                    stats['skipped'] += 1
                    continue
                
                # 记录
                if not dry_run:
                    # Try SQLite first, fall back to JSON
                    try:
                        from database import add_score_entry
                        add_score_entry(
                            date_str=date_str,
                            activity=act,
                            points=cfg['points'],
                            label=f"{cfg['label']}（云端同步）",
                            source='cloud_sync',
                            source_id=f"sync_{chat_id}_{act}",
                            chat_id=str(chat_id),
                            time_str=time_str,
                        )
                    except Exception:
                        add_activity_record(game_data, date_str, act, cfg['points'], 
                                          f"{cfg['label']}（云端同步）", 'cloud_sync')
                    print(f"    ✅ {cfg['label']} +{cfg['points']}  (duration={cand.get('duration_min', duration_min)}min)")
                    stats['added'] += 1
                else:
                    print(f"    📋 [DRY-RUN] 将添加 {cfg['label']} +{cfg['points']}")
                    stats['added'] += 1
        
        # 记录已同步（即使没有添加记录）
        if not dry_run:
            synced_ids.add(str(chat_id))
    
    # 保存
    if not dry_run:
        sync_log['synced_chats'] = sorted(synced_ids)
        save_sync_log(sync_log)
        save_game_data(game_data)
    
    print(f"\n📊 同步完成:")
    print(f"   扫描: {stats['scanned']} 条聊天")
    print(f"   新增: {stats['added']} 条记录")
    print(f"   跳过: {stats['skipped']} 条（已达上限）")
    if stats['added'] > 0 and not dry_run:
        print(f"   当前总分: {game_data.get('total_score', 0)}")


def verify_and_fix():
    """全量验证并修复所有数据。"""
    print("🔍 全量数据验证中...\n")
    auth = load_auth()
    session = get_session(auth)
    base = auth.get('CLOUD_BASE', 'https://xiaozhi.me')
    
    game_data = load_game_data()
    all_chats = fetch_all_chats(session, base)
    
    # 构建云端活动记录
    cloud_activities = {}  # date -> {activity: count}
    
    for chat in all_chats:
        created = chat['created_at'][:19]
        bj = utc_to_beijing(created)
        date_str = bj.strftime('%Y-%m-%d')
        duration_min = chat.get('duration', 0) // 60
        
        title = (chat.get('chat_summary') or {}).get('title', '')
        summary = (chat.get('chat_summary') or {}).get('summary', '')
        
        if duration_min < 5:
            continue
        
        candidates = classify_chat_by_summary(title, summary, duration_min, chat.get('msg_count', 0))
        
        # 下载消息精确判断
        if candidates:
            msgs = fetch_chat_messages(session, base, chat['id'])
            detailed = classify_chat_by_messages(msgs, duration_min)
            if detailed:
                for d in detailed:
                    act = d['activity']
                    if date_str not in cloud_activities:
                        cloud_activities[date_str] = {}
                    cloud_activities[date_str][act] = cloud_activities[date_str].get(act, 0) + 1
    
    # 对比本地记录
    print("📋 云端 vs 本地 对比:\n")
    total_fixed = 0
    
    for date_str in sorted(cloud_activities.keys()):
        for act, cloud_count in cloud_activities[date_str].items():
            # 查询数据库中的实际记录数（而非从 JSON 读取）
            try:
                from database import get_daily_count
                local_count = get_daily_count(date_str, act)
            except ImportError:
                local_count = has_activity_on_date(game_data, date_str, act)
            cfg = ACTIVITY_CONFIG.get(act, {})
            max_per_day = cfg.get('max_per_day', 999)
            points = cfg.get('points', 15)
            label = cfg.get('label', act)
            
            # 云端有，本地没有或不够 → 补
            needed = min(cloud_count, max_per_day) - local_count
            if needed > 0:
                for _ in range(needed):
                    add_activity_record(game_data, date_str, act, points, f"{label}（云端同步）", 'cloud_sync')
                    total_fixed += 1
                    print(f"  ✅ {date_str} {label} +{points} (云端{cloud_count}次, 本地{local_count}次, 补{needed}次)")
    
    if total_fixed > 0:
        save_game_data(game_data)
        print(f"\n✅ 共补录 {total_fixed} 条, 总分: {game_data.get('total_score', 0)}")
    else:
        print("✅ 所有数据已准确，无需修正")


if __name__ == '__main__':
    args = sys.argv[1:]
    
    if '--verify' in args:
        verify_and_fix()
    elif '--dry-run' in args:
        sync(dry_run=True, force_full='--full' in args)
    elif '--full' in args:
        sync(force_full=True)
    elif '--chat' in args:
        idx = args.index('--chat')
        if idx + 1 < len(args):
            sync(single_chat=int(args[idx + 1]))
        else:
            print("⚠️  请指定 chat_id: --chat 12345")
    else:
        sync()
