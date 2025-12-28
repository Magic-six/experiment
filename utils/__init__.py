"""
工具模块 - 包含辅助函数和配置
"""

# 直接导入需要的函数，避免循环引用
from .utils import setup_logging, mini_one_share, mini_zero_share, generate_triples

# 按需导入配置参数，需要时直接导入对应变量
# 避免在此处全部导入造成循环引用问题

__all__ = [
    'setup_logging', 
    'mini_one_share', 
    'mini_zero_share', 
    'generate_triples'
]
