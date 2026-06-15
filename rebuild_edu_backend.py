#!/usr/bin/env python3
"""Rebuild edu_backend.py from pyc constants."""
import marshal

with open("__pycache__/edu_backend.cpython-311.pyc", "rb") as f:
    all_data = f.read()

code_obj = marshal.loads(all_data[16:])

# Extract all top-level function constants
func_data = {}
for const in code_obj.co_consts:
    if hasattr(const, 'co_name') and hasattr(const, 'co_consts'):
        strings = {}
        for i, c in enumerate(const.co_consts):
            if isinstance(c, str) and len(c) > 5:
                strings[i] = c
            elif hasattr(c, 'co_code') and not isinstance(c, str):
                for j, inner in enumerate(c.co_consts):
                    if isinstance(inner, str) and len(inner) > 5:
                        strings[f"{i}.{j}"] = inner
        func_data[const.co_name] = {
            'line': const.co_firstlineno,
            'strings': strings,
            'code': const,
            'all_consts': const.co_consts,
        }

print("Functions:", {k: v['line'] for k, v in func_data.items()})

# Save function data as JSON for the main builder
import json
output = {}
for fname, fd in func_data.items():
    s = fd['strings']
    output[fname] = {
        'line': fd['line'],
        'strings': {str(k): v for k, v in s.items()},
        'nconsts': len(fd['all_consts']),
    }

with open("/tmp/func_data.json", "w") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
    
print(f"Saved to /tmp/func_data.json ({len(output)} functions)")

# Also save all strings by function
for fname, fd in func_data.items():
    print(f"\n=== {fname} ===")
    for idx, s in sorted(fd['strings'].items(), key=lambda x: x[0]):
        print(f"  [{idx}] ({len(s)}): {s[:150]}")
