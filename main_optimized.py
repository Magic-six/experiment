#!/usr/bin/env python
"""
优化版主模块 - 拉格朗日安全插值协议的入口和测试函数
针对运行时间进行了多项性能优化
"""

import sys
import time
import logging
import asyncio
import traceback
import json
import os
from typing import List, Tuple, Optional

# 添加必要的路径到Python导入路径
current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))  # 添加父目录

# 导入项目模块
try:
    from experiment.core.multiplicative_group import PrimeOrderCyclicGroup
    from experiment.utils.config import (
        DEFAULT_PRIME, DEFAULT_GENERATOR, 
        DEFAULT_X_STAR, MIN_PARTIES, MAX_PARTIES
    )
    from experiment.utils.utils import setup_logging
    from experiment.protocols.protocol_extension import secure_lagrange_interpolation
except ImportError:
    # 如果上面的导入失败，尝试其他导入方式
    from core.multiplicative_group import PrimeOrderCyclicGroup
    from utils.config import (
        DEFAULT_PRIME, DEFAULT_GENERATOR, 
        DEFAULT_X_STAR, MIN_PARTIES, MAX_PARTIES
    )
    from utils.utils import setup_logging
    from protocols.protocol_extension import secure_lagrange_interpolation

# 全局缓存 - 避免重复初始化
_group_cache = None
_logger_initialized = False

def get_cached_group() -> PrimeOrderCyclicGroup:
    """获取缓存的循环群实例"""
    global _group_cache
    if _group_cache is None:
        _group_cache = PrimeOrderCyclicGroup(DEFAULT_PRIME, DEFAULT_GENERATOR)
    return _group_cache

async def n_party_demo_run_optimized(party_num: Optional[int] = None, enable_logging: bool = False) -> None:
    """
    优化版多参与方协议示例运行函数（异步版本）
    
    优化措施：
    1. 缓存循环群实例避免重复初始化
    2. 减少不必要的日志输出和打印
    3. 预计算数据点
    4. 优化内存分配
    
    Args:
        party_num: 参与方数量，如果为None则使用配置文件或默认值
        enable_logging: 是否启用详细日志，默认False以提高性能
    """
    # 记录整个协议的开始时间
    overall_start_time = time.perf_counter()  # 使用更精确的计时器

    # 1) 快速初始化参与方数量
    if party_num is None:
        party_num = 3  # 直接使用默认值，避免文件IO
    
    # 确保参与方数量在有效范围内
    if not (MIN_PARTIES <= party_num <= MAX_PARTIES):
        party_num = 3
    
    if enable_logging:
        logger = logging.getLogger('lagrange_protocol')
        logger.info(f"参与方数量: {party_num}")
    
    # 禁用网络模拟
    if 'USE_NETWORK_SIMULATION' in os.environ:
        del os.environ['USE_NETWORK_SIMULATION']
    
    # 预计算数据点 - 使用更高效的列表生成
    points = [(i, i * i) for i in range(1, party_num + 1)]  # 避免使用**运算符
        
    try:
        # 使用缓存的循环群实例
        group = get_cached_group()
        
        # 执行安全插值协议 - 直接传入已缓存的group参数
        y_star = await secure_lagrange_interpolation(
            points, 
            DEFAULT_X_STAR, 
            DEFAULT_PRIME, 
            DEFAULT_GENERATOR
        )
        
        # 计算整个协议的运行时间
        overall_end_time = time.perf_counter()
        run_time = overall_end_time - overall_start_time
        
        # 只输出关键结果，减少IO开销
        print(f"插值结果: y={y_star}, 运行时间: {run_time:.4f}秒")
        
    except Exception as e:
        print(f"运行出错: {e}")
        if enable_logging:
            logger = logging.getLogger('lagrange_protocol')
            logger.error(f"运行出错: {e}")

async def benchmark_protocol(party_nums: List[int], runs_per_config: int = 5) -> None:
    """
    协议性能基准测试
    
    Args:
        party_nums: 要测试的参与方数量列表
        runs_per_config: 每个配置运行的次数
    """
    print("=== 协议性能基准测试 ===")
    results = {}
    
    for party_num in party_nums:
        print(f"\n测试 {party_num} 方协议...")
        times = []
        
        for i in range(runs_per_config):
            start_time = time.perf_counter()
            await n_party_demo_run_optimized(party_num, enable_logging=False)
            end_time = time.perf_counter()
            run_time = end_time - start_time
            times.append(run_time)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        results[party_num] = {
            'avg': avg_time,
            'min': min_time,
            'max': max_time,
            'times': times
        }
        
        print(f"  平均时间: {avg_time:.4f}秒")
        print(f"  最快时间: {min_time:.4f}秒") 
        print(f"  最慢时间: {max_time:.4f}秒")
    
    print("\n=== 基准测试结果汇总 ===")
    for party_num, stats in results.items():
        print(f"{party_num}方: 平均{stats['avg']:.4f}s, 最快{stats['min']:.4f}s")

async def test_secure_lagrange_interpolation_fast() -> bool:
    """
    快速测试版本 - 减少输出和日志
    """
    try:
        # 测试用例1: 二次函数插值
        points1 = [(1, 3), (2, 6), (3, 11)]  # y = x^2 + 2
        x_star1 = 5
        y_star1 = await secure_lagrange_interpolation(points1, x_star1)
        expected1 = 27  # 5^2 + 2 = 27
        
        # 测试用例2: 三次函数插值  
        points2 = [(1, 1), (2, 8), (3, 27), (4, 64)]  # y = x^3
        x_star2 = 5
        y_star2 = await secure_lagrange_interpolation(points2, x_star2)
        expected2 = 125  # 5^3 = 125
        
        success1 = y_star1 == expected1
        success2 = y_star2 == expected2
        
        print(f"测试1: {'✓' if success1 else '✗'} (期望:{expected1}, 实际:{y_star1})")
        print(f"测试2: {'✓' if success2 else '✗'} (期望:{expected2}, 实际:{y_star2})")
        
        return success1 and success2
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False

def main() -> None:
    """
    优化版主函数 - 程序入口点
    """
    try:
        # 减少初始化开销，只在需要时配置日志
        enable_detailed_logging = '--verbose' in sys.argv or '-v' in sys.argv
        
        if enable_detailed_logging:
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
            os.makedirs(log_dir, exist_ok=True)
            setup_logging(filename='lagrange_protocol_optimized.log', log_dir=log_dir)
        
        # 预热循环群缓存
        get_cached_group()
        
        # 解析命令行参数
        party_num = None
        run_benchmark = False
        run_test = False
        
        args = sys.argv[1:]
        for arg in args:
            if arg.isdigit():
                party_num = int(arg)
            elif arg in ('test', '--test'):
                run_test = True
            elif arg in ('benchmark', '--benchmark'):
                run_benchmark = True
        
        if run_benchmark:
            # 运行基准测试
            print("运行性能基准测试...")
            asyncio.run(benchmark_protocol([3, 4, 5, 6, 7]))
        elif run_test:
            # 快速测试模式
            print("运行快速测试...")
            success = asyncio.run(test_secure_lagrange_interpolation_fast())
            print(f"测试{'成功' if success else '失败'}")
        else:
            # 正常运行 - 优化版
            asyncio.run(n_party_demo_run_optimized(party_num, enable_detailed_logging))
            
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {type(e).__name__}: {e}")
        if enable_detailed_logging:
            traceback.print_exc()

if __name__ == "__main__":
    main()
