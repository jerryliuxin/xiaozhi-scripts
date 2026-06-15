#!/usr/bin/env python3.11
import sys
sys.path.insert(0, '/Users/mihua/.hermes/xiaozhi_scripts')

import importlib.util, dis, types

# 直接从 pyc 加载
spec = importlib.util.spec_from_file_location('edu_backend_orig', '/Users/mihua/.hermes/xiaozhi_scripts/__pycache__/edu_backend.cpython-311.pyc')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# 从 dis 输出中重建源码
# 关键是：Python 3.11 的 dis 模块提供行号信息
# 我们可以从 instruction 中重建源码行

# 获取所有函数的代码对象
all_funcs = {}
for name in dir(mod):
    if not name.startswith('__'):
        obj = getattr(mod, name)
        if hasattr(obj, '__code__'):
            all_funcs[name] = obj.__code__

# 对于每个函数，获取其指令的行号映射
# Python 3.11+ 使用 co_lines() 来获取行号映射
# dis.get_instructions() 会返回带有 positions.lineno 的指令

for name, code_obj in all_funcs.items():
    print(f'=== {name} (L{code_obj.co_firstlineno}) ===')
    instructions = list(dis.get_instructions(code_obj))
    
    # 获取行号映射
    line_map = {}
    for start, end, ln in code_obj.co_lines():
        for offset in range(start, end):
            line_map[offset] = ln
    
    # 打印每条指令
    for instr in instructions[:50]:  # 前50条
        lineno = instr.positions.lineno if hasattr(instr, 'positions') and instr.positions else None
        print(f"  offset={instr.offset:4d} L{lineno:4d} {instr.opname:20s} {instr.argval!r}")
    
    if len(instructions) > 50:
        print(f"  ... ({len(instructions)} total instructions)")
