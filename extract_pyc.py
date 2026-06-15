#!/usr/bin/env python3.11
import sys
sys.path.insert(0, '/Users/mihua/.hermes/xiaozhi_scripts')

import importlib.util

# 直接从 pyc 加载，不经过 edu_backend.py stub
spec = importlib.util.spec_from_file_location('edu_backend_orig', '/Users/mihua/.hermes/xiaozhi_scripts/__pycache__/edu_backend.cpython-311.pyc')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import inspect

# 获取所有顶层函数的源码
for name in dir(mod):
    if not name.startswith('__'):
        obj = getattr(mod, name)
        if hasattr(obj, '__code__'):
            try:
                src = inspect.getsource(obj)
                print(f'\n=== {name} ===')
                print(src)
            except:
                print(f'\n=== {name} === (source not available)')

# 也获取顶层模块常量
print('\n\n=== Top-level constants ===')
for name in ['AUTO_RECORD_MAP', 'STORIES_MAP', 'NEWS_TOPICS', 'QUIZ_QUESTIONS', 'RECYCLING_QUESTIONS', 'KNOWLEDGE_BASE']:
    if hasattr(mod, name):
        val = getattr(mod, name)
        print(f'{name} = {val}')
