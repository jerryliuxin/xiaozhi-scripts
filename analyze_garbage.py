import json
from collections import defaultdict

with open('/Users/mihua/.hermes/xiaozhi_scripts/game_data.json') as f:
    data = json.load(f)

records = data['history']

print('=' * 120)
print('DETAILED ANALYSIS OF ALL 69 RECORDS')
print('=' * 120)

# Group by second for batch detection
second_groups = defaultdict(list)
for i, r in enumerate(records):
    ts = r['time']
    second_key = ts[:19]
    second_groups[second_key].append((i, r))

# Find batches (>=3 records within same second)
batch_seconds = {k: v for k, v in second_groups.items() if len(v) >= 3}
print(f'\nSeconds with >=3 records (batch indicator): {len(batch_seconds)}')
for sec, items in sorted(batch_seconds.items()):
    print(f'  {sec}: {len(items)} records -> indices {[idx for idx,_ in items]}')

# Classify records
garbage_indices = []
garbage_reasons = []
maybe_real_indices = []

# Record #1: test_cli
garbage_indices.append(0)
garbage_reasons.append('EXPLICIT CLI TEST: activity=test_cli, label=CLI测试')

# Records #2-27 (indices 1-26): 2026-06-14 bulk batches
for idx in range(1, 27):
    r = records[idx]
    ts = r['time']
    second_key = ts[:19]

    if second_key in batch_seconds:
        garbage_indices.append(idx)
        reason_parts = ['BATCH record']
        if r.get('label') in ('', None):
            reason_parts.append('no description')
        if r['activity'] == 'penalty' and r.get('extra', {}).get('penalty_type') == '':
            reason_parts.append('empty penalty_type')
        if r['activity'] == 'chore' and r.get('extra', {}).get('chore_type') == 'other':
            reason_parts.append('generic chore_type')
        garbage_reasons.append('; '.join(reason_parts))

# Record #28 (index 27): 2026-06-15 single praise
ts_28 = records[27]['time']
if ts_28[:19] in batch_seconds:
    garbage_indices.append(27)
    garbage_reasons.append('BATCH record')
else:
    maybe_real_indices.append(27)

# Records #29-31 (indices 28-30): 2026-07-15
for idx in range(28, 31):
    if records[idx]['time'][:19] in batch_seconds:
        garbage_indices.append(idx)
        garbage_reasons.append('BATCH record (3 records in 14ms)')
    else:
        maybe_real_indices.append(idx)

# Records #32-33 (indices 31-32): 2026-07-21
for idx in range(31, 33):
    if records[idx]['time'][:19] in batch_seconds:
        garbage_indices.append(idx)
        garbage_reasons.append('BATCH record')
    else:
        maybe_real_indices.append(idx)

# Records #34-69 (indices 33-68): 2026-07-24 bulk
for idx in range(33, 69):
    r = records[idx]
    ts = r['time']
    second_key = ts[:19]

    if second_key in batch_seconds:
        garbage_indices.append(idx)
        reasons = ['BATCH record']

        if r['activity'] == 'story_song' and r['total'] == 0:
            same_sec_count = sum(1 for j in range(33, 69) if records[j]['time'][:19] == second_key and records[j]['activity'] == 'story_song')
            if same_sec_count > 3:
                reasons.append(f'story_song spam x{same_sec_count}')

        if second_key == '2026-07-24T13:02:31':
            reasons.append('12 activities in 0.115s (automated)')

        garbage_reasons.append('; '.join(reasons))
    else:
        garbage_indices.append(idx)
        garbage_reasons.append('adjacent to batch cluster (same automated session)')

# Summary
print(f'\n### CLASSIFICATION SUMMARY ###')
print(f'Total records: {len(records)}')
print(f'Garbage records: {len(garbage_indices)}')
print(f'Potentially real records: {len(maybe_real_indices)}')
print(f'Garbage ratio: {len(garbage_indices) / len(records) * 100:.1f}%')

total_garbage_score = sum(records[i]['total'] for i in garbage_indices)
total_maybe_score = sum(records[i]['total'] for i in maybe_real_indices)
claimed_total = data['total_score']

print(f'')
print(f'Garbage total score: {total_garbage_score}')
print(f'Potentially real total score: {total_maybe_score}')
print(f'Claimed total_score field: {claimed_total}')
print(f'Sum of all record totals: {sum(r["total"] for r in records)}')
print(f'Garbage score proportion: {total_garbage_score / claimed_total * 100:.1f}%')

print(f'\n### GARBAGE RECORDS DETAILED ###')
header = f'{"#":>3s} | {"Time":>30s} | {"Activity":>25s} | {"Total":>5s} | Reason'
print(header)
print('-' * 120)
for idx in sorted(garbage_indices):
    r = records[idx]
    reason_idx = garbage_indices.index(idx)
    print(f'{idx+1:3d} | {r["time"]:>30s} | {r["activity"]:>25s} | {r["total"]:5d} | {garbage_reasons[reason_idx]}')

print(f'\n### POTENTIALLY REAL RECORDS ###')
for idx in sorted(maybe_real_indices):
    r = records[idx]
    print(f'{idx+1:3d} | {r["time"]:>30s} | {r["activity"]:>25s} | {r["total"]:5d} | label={r.get("label","")}')

print(f'\n### BATCH ANALYSIS ###')
print(f'Batch seconds (>=3 records in same second): {len(batch_seconds)}')
for sec, items in sorted(batch_seconds.items()):
    activities = [(records[i]['activity'], records[i]['total']) for i, _ in items]
    print(f'  {sec} ({len(items)} records):')
    for act, total in activities:
        print(f'    - {act:30s} total={total}')