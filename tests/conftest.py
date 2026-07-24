"""pytest 配置"""
import os
import sys
from pathlib import Path
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

# 标记测试来源，积分记录会被标记 source='test'
os.environ.setdefault('XIAOZHI_SOURCE', 'test')
