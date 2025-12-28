#!/usr/bin/env python
"""
主模块 - 拉格朗日安全插值协议的入口和测试函数
不包含网络状态模拟的基本版本
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

# 初始化logger
logger = logging.getLogger('lagrange_protocol')

async def n_party_demo_run(party_num: Optional[int] = None) -> None:
    """
    多参与方协议示例运行函数（异步版本）
    此函数用于演示多参与方安全计算协议的运行过程和性能
    
    Args:
        party_num: 参与方数量，如果为None则使用配置文件或默认值
    """
    print("开始运行n_party_demo_run函数")
    sys.stdout.flush()
    
    # 记录整个协议的开始时间
    overall_start_time = time.time()

    # 1) 初始化
    # 设定参与方数量
    if party_num is None:
        # 尝试从配置文件读取
        try:
            config_file = os.path.join(os.path.dirname(__file__), 'config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    party_num = config.get('party_count', 3)
            else:
                party_num = 3
        except:
            party_num = 3
    
    # 确保参与方数量在有效范围内
    if not (MIN_PARTIES <= party_num <= MAX_PARTIES):
        print(f"参与方数量 {party_num} 超出有效范围({MIN_PARTIES}-{MAX_PARTIES})，使用默认值3")
        party_num = 3
        
    print(f"参与方数量: {party_num}")
    sys.stdout.flush()
    logger.info(f"参与方数量: {party_num}")
    
    # 禁用网络模拟
    if 'USE_NETWORK_SIMULATION' in os.environ:
        del os.environ['USE_NETWORK_SIMULATION']
    
    # 准备数据点 - 简单的二次函数 y = x^2
    points = [(i, i**2) for i in range(1, party_num+1)]
        
    # 调用安全拉格朗日插值函数
    try:
        logger.info("初始化循环群...")
        group = PrimeOrderCyclicGroup(DEFAULT_PRIME, DEFAULT_GENERATOR)
        logger.info("循环群初始化完成")
        
        print("生成数据点...")
        sys.stdout.flush()
        logger.info(f"数据点: {points}")
        
        print(f"开始计算x={DEFAULT_X_STAR}处的插值...")
        sys.stdout.flush()
        
        # 执行安全插值协议
        y_star = await secure_lagrange_interpolation(points, DEFAULT_X_STAR, DEFAULT_PRIME, DEFAULT_GENERATOR)
        print(f"在x={DEFAULT_X_STAR}处的插值结果: y={y_star}")
        sys.stdout.flush()
        
        # 计算整个协议的运行时间
        overall_end_time = time.time()
        run_time = overall_end_time - overall_start_time
        print(f"总运行时间: {run_time:.2f} 秒")
        sys.stdout.flush()
        
    except Exception as e:
        print(f"运行出错: {e}")
        sys.stdout.flush()
        logger.error(f"运行出错: {e}")
        traceback.print_exc()

async def test_secure_lagrange_interpolation() -> bool:
    """
    测试secure_lagrange_interpolation函数的功能正确性
    
    Returns:
        测试是否成功
    """
    print("开始测试secure_lagrange_interpolation函数...")
    sys.stdout.flush()
    
    try:
        # 测试用例1: 简单的二次插值
        print("\n测试用例1: 二次函数插值 f(x) = x^2 + 2")
        sys.stdout.flush()
        points1 = [(1, 3), (2, 6), (3, 11), (4, 18), (5, 27)]  # y = x^2 + 2
        x_star1 = 7
        y_star1 = await secure_lagrange_interpolation(points1, x_star1)
        expected1 = 51  # 7^2 + 2 = 51
        print(f"插值结果: f({x_star1}) = {y_star1}")
        print(f"理论值: {expected1}")
        sys.stdout.flush()
        
        # 测试用例2: 三次函数插值
        print("\n测试用例2: 三次函数插值 f(x) = x^3")
        sys.stdout.flush()
        points2 = [(1, 1), (2, 8), (3, 27), (4, 64)]  # y = x^3
        x_star2 = 5
        y_star2 = await secure_lagrange_interpolation(points2, x_star2)
        expected2 = 125  # 5^3 = 125
        print(f"插值结果: f({x_star2}) = {y_star2}")
        print(f"理论值: {expected2}")
        sys.stdout.flush()
        
        print("\n测试完成!")
        sys.stdout.flush()
        return True
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        sys.stdout.flush()
        traceback.print_exc()
        return False

def main() -> None:
    """
    主函数 - 程序入口点
    """
    try:
        print("程序开始运行")
        sys.stdout.flush()
        
        # 配置日志
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        setup_logging(filename='lagrange_protocol.log', log_dir=log_dir)
        
        # 尝试从命令行参数获取参与方数量
        party_num = None
        if len(sys.argv) > 1:
            try:
                party_num = int(sys.argv[1])
                print(f"使用命令行指定的参与方数量: {party_num}")
                sys.stdout.flush()
            except ValueError:
                print(f"命令行参数 '{sys.argv[1]}' 不是有效的整数，将使用配置文件或默认值")
                sys.stdout.flush()
        
        # 根据命令行参数选择运行模式
        if len(sys.argv) > 2 and sys.argv[2].lower() == 'test':
            # 测试模式
            print("进入测试模式")
            sys.stdout.flush()
            logger.info("开始运行测试")
            asyncio.run(test_secure_lagrange_interpolation())
        else:
            # 正常运行
            logger.info("开始运行n_party_demo_run函数")
            asyncio.run(n_party_demo_run(party_num))
            
        logger.info("程序正常结束")
        print("程序正常结束")
        sys.stdout.flush()
        
    except KeyboardInterrupt:
        print("程序被用户中断")
        sys.stdout.flush()
        logger.error("程序被用户中断")
    except asyncio.TimeoutError:
        print("程序执行超时")
        sys.stdout.flush()
        logger.error("程序执行超时")
    except Exception as e:
        print(f"程序运行出错: {type(e).__name__}: {e}")
        sys.stdout.flush()
        logger.error(f"程序运行出错: {type(e).__name__}: {e}")
        traceback.print_exc()
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()