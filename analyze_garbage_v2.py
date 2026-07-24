import json
from collections import defaultdict

with open('/Users/mihua/.hermes/xiaozhi_scripts/game_data.json') as f:
    data = json.load(f)

records = data['history']

print('=' * 120)
print('CORRECTED ANALYSIS OF ALL 69 RECORDS')
print('=' * 120)

# Group by second
second_groups = defaultdict(list)
for i, r in enumerate(records):
    second_key = r['time'][:19]
    second_groups[second_key].append((i, r))

batch_seconds = {k: v for k, v in second_groups.items() if len(v) >= 3}
print(f'Batch seconds (>=3 records in same second): {len(batch_seconds)}')

# === CLASSIFICATION LOGIC ===
# Identify logically grouped "sessions" based on time proximity
# A "real" voice session: activities spread out with real descriptions

garbage_idx = set()
maybe_real_idx = set()

# --- SESSION 1: 2026-06-14 entire block (indices 0-26, records #1-#27) ---
# Record #1: explicit CLI test
# Records #2-#27: all on same day, after CLI test, in tight time clusters
# - Batches at 12:06, 12:09, 12:14, 12:16
# - All penalties have empty penalty_type ("")
# - All chores have generic type "other"
# - No actual scene descriptions
# - Pattern: unlock+english_quiz always paired within same second, then batch of chores/penalties
# This is clearly automated CLI testing
for idx in range(0, 27):
    garbage_idx.add(idx)

# --- RECORD #28 (index 27): 2026-06-15 single praise ---
# Single isolated record. No batch pattern. Could be real (voice triggered praise).
maybe_real_idx.add(27)

# --- SESSION: 2026-07-15 (indices 28-30, records #29-#31) ---
# 3 records in 0.014 seconds — batch
for idx in range(28, 31):
    garbage_idx.add(idx)

# --- RECORDS #32-33 (indices 31-32): 2026-07-21 two unlocks ---
# 10 minutes apart. Could be real voice interactions.
maybe_real_idx.add(31)
maybe_real_idx.add(32)

# --- SESSION: 2026-07-24 entire block (indices 33-68, records #34-#69) ---
# Clear automated batch:
# - 8 story_song records in 1 second (13:01:34)
# - 4 story_song records in 0.045s (13:01:41)
# - 12 DIFFERENT activities in 0.115s (13:02:31) — impossible for real voice
# - Duplicate daily_complete at 13:01:22 and 13:01:24
for idx in range(33, 69):
    garbage_idx.add(idx)

# === VERIFY COVERAGE ===
all_accounted = garbage_idx | maybe_real_idx
if all_accounted != set(range(69)):
    missing = set(range(69)) - all_accounted
    print(f'WARNING: Missing indices: {missing}')

# === SUMMARY ===
print(f'\n### SUMMARY ###')
print(f'Total records: {len(records)}')
print(f'Garbage: {len(garbage_idx)} ({len(garbage_idx)/len(records)*100:.1f}%)')
print(f'Potentially real: {len(maybe_real_idx)} ({len(maybe_real_idx)/len(records)*100:.1f}%)')

garbage_score = sum(records[i]['total'] for i in garbage_idx)
real_score = sum(records[i]['total'] for i in maybe_real_idx)
all_score = sum(r['total'] for r in records)
claimed = data['total_score']

print(f'Garbage score total: {garbage_score}')
print(f'Potentially real score total: {real_score}')
print(f'Sum of all record totals: {all_score} (matches claimed: {all_score == claimed})')

# === GARBAGE LIST ===
print(f'\n### ALL GARBAGE RECORDS ###')
print(f'{"#":>3s} | {"Time":>30s} | {"Activity":>25s} | {"Total":>5s} | Indicators')
print('-' * 120)

for idx in sorted(garbage_idx):
    r = records[idx]
    indicators = []
    
    # Direct source indicators
    if r['activity'] == 'test_cli' or r.get('label') == 'CLI测试':
        indicators.append('EXPLICIT CLI TEST')
    
    # Batch/same-second indicators
    if r['time'][:19] in batch_seconds:
        count = len(second_groups[r['time'][:19]])
        indicators.append(f'same-second batch x{count}')
    
    # Empty/null fields
    if r.get('label') in ('', None) and r['activity'] not in ('praise', '_multi_bonus_applied', 'mickey_f1', 'story_song', 'adventure', 'news_topic', 'knowledge'):
        indicators.append('no description')
    if r['activity'] == 'penalty' and r.get('extra', {}).get('penalty_type') == '':
        indicators.append('empty penalty_type')
    if r['activity'] == 'chore' and r.get('extra', {}).get('chore_type') == 'other':
        indicators.append('generic chore_type')
    
    # Duplicate
    if r['activity'] == 'daily_complete':
        same_day_dup = sum(1 for j in garbage_idx if records[j]['date'] == r['date'] and records[j]['activity'] == 'daily_complete')
        if same_day_dup > 1:
            indicators.append(f'duplicate daily_complete x{same_day_dup}')
    
    # story_song spam
    if r['activity'] == 'story_song':
        sec = r['time'][:19]
        if sec in batch_seconds:
            cnt = sum(1 for i, _ in second_groups[sec] if records[i]['activity'] == 'story_song')
            if cnt > 3:
                indicators.append(f'story_song spam x{cnt}')
    
    # 12 activities in 0.115s
    if r['time'][:19] == '2026-07-24T13:02:31':
        indicators.append('12 acts in 0.115s impossible')
    
    print(f'{idx+1:3d} | {r["time"]:>30s} | {r["activity"]:>25s} | {r["total"]:5d} | {", ".join(indicators)}')

# === POTENTIALLY REAL LIST ===
print(f'\n### POTENTIALLY REAL RECORDS (only {len(maybe_real_idx)}) ###')
print(f'{"#":>3s} | {"Time":>30s} | {"Activity":>25s} | {"Total":>5s} | Details')
print('-' * 80)
for idx in sorted(maybe_real_idx):
    r = records[idx]
    print(f'{idx+1:3d} | {r["time"]:>30s} | {r["activity"]:>25s} | {r["total"]:5d} | label={r.get("label","")}')

# === SESSION BREAKDOWN ===
print(f'\n### SESSION BREAKDOWN ###')
sessions = {
    '2026-06-14 CLI Test Session': (0, 26),
    '2026-06-15 Isolated Praise': (27, 27),
    '2026-07-15 Batch': (28, 30),
    '2026-07-21 Real(?): 2 unlocks': (31, 32),
    '2026-07-24 Automated Batch': (33, 68),
}
for name, (start, end) in sessions.items():
    count = end - start + 1
    score = sum(records[i]['total'] for i in range(start, end+1))
    is_garbage = all(i in garbage_idx for i in range(start, end+1))
    is_real = all(i in maybe_real_idx for i in range(start, end+1))
    status = 'GARBAGE' if is_garbage else ('REAL?' if is_real else 'MIXED')
    print(f'  {name}: {count} records, score={score}, status={status}')