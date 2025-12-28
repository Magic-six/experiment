"""
主模块 - 包含主程序入口和测试函数
"""

import sys
import time
import logging
import asyncio
import traceback
import json
import os
from typing import List, Tuple, Optional

from multiplicative_group import PrimeOrderCyclicGroup
from utils import setup_logging
from protocol_extension import secure_lagrange_interpolation
from config import (
    DEFAULT_PRIME, DEFAULT_GENERATOR, 
    DEFAULT_X_COORDS, DEFAULT_Y_COORDS,
    DEFAULT_X_STAR, MIN_PARTIES, MAX_PARTIES
)

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
    # 记录整个协议的开始时间
    overall_start_time = time.time()

    # 1) 初始化
    # 设定参与方数量
    if party_num is None:
        # 尝试从配置文件读取
        try:
            config_file = 'config.json'
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

    # 准备数据点
    points = []
    for i in range(1, party_num+1):
        if i < len(DEFAULT_X_COORDS):
            points.append((DEFAULT_X_COORDS[i], DEFAULT_Y_COORDS[i]))
        else:
            # 如果默认坐标不足，添加额外的点
            points.append((i, i*i))
            
    # 调用安全拉格朗日插值函数
    try:
        y_star = await secure_lagrange_interpolation(points, DEFAULT_X_STAR)
        print(f"在x={DEFAULT_X_STAR}处的插值结果: y={y_star}")
        
        # 计算整个协议的运行时间
        overall_end_time = time.time()
        run_time = overall_end_time - overall_start_time
        print(f"总运行时间: {run_time:.2f} 秒")
        
    except Exception as e:
        print(f"运行出错: {e}")
        traceback.print_exc()

async def test_secure_lagrange_interpolation() -> bool:
    """
    测试secure_lagrange_interpolation函数的功能正确性
    
    Returns:
        测试是否成功
    """
    print("开始测试secure_lagrange_interpolation函数...")
    
    try:
        # 测试用例1: 简单的线性插值
        print("\n测试用例1: 简单的线性插值")
        points1 = [(0, 2), (2, 6), (3, 11), (4, 18), (5, 27), (6, 38), (7, 51), (8, 66)]  # y = x^2 + 2
        x_star1 = 9
        y_star1 = await secure_lagrange_interpolation(points1, x_star1)
        print(f"插值结果: f({x_star1}) = {y_star1}")
        print(f"理论值: 83")
        
        # 可以添加更多测试用例
        # # 测试用例2: 非线性插值
        # print("\n测试用例2: 非线性插值")
        # points2 = [(1, 1), (2, 4), (3, 9)]  # y = x^2
        # x_star2 = 4
        # y_star2 = await secure_lagrange_interpolation(points2, x_star2)
        # print(f"插值结果: f({x_star2}) = {y_star2}")
        # print(f"理论值: 16")
        
        print("\n测试完成!")
        return True
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        traceback.print_exc()
        return False

def main() -> None:
    """
    主函数 - 程序入口点
    """
    try:
        print("程序开始运行")
        # 配置日志
        setup_logging(filename='lagrange_protocol.log', console_output=True)
        
        # 尝试从命令行参数获取参与方数量
        party_num = None
        if len(sys.argv) > 1:
            try:
                party_num = int(sys.argv[1])
            except ValueError:
                print(f"命令行参数 '{sys.argv[1]}' 不是有效的整数，将使用配置文件或默认值")
        
        # 根据命令行参数选择运行模式
        if len(sys.argv) > 2 and sys.argv[2].lower() == 'test':
            # 测试模式
            logger.info("开始运行测试")
            asyncio.run(test_secure_lagrange_interpolation())
        else:
            # 正常运行
            logger.info("开始运行n_party_demo_run函数")
            asyncio.run(n_party_demo_run(party_num))
            
        logger.info("程序正常结束")
        print("程序正常结束")
        
    except KeyboardInterrupt:
        print("程序被用户中断")
        logger.error("程序被用户中断")
    except asyncio.TimeoutError:
        print("程序执行超时")
        logger.error("程序执行超时")
    except Exception as e:
        print(f"程序运行出错: {type(e).__name__}: {e}")
        logger.error(f"程序运行出错: {type(e).__name__}: {e}")
        traceback.print_exc()
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
