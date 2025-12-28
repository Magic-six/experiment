"""
网络测试运行脚本 - 运行不同网络环境下的拉格朗日协议测试并生成比较报告
"""

import asyncio
import argparse
import os
import time
import sys
from typing import List, Dict, Any

from network_test import run_all_tests, plot_results
from utils import setup_logging
from network_simulator import NETWORK_CONDITIONS

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行拉格朗日协议网络环境测试")
    parser.add_argument("--networks", nargs="+", default=["local", "lan", "wan", "iot"], 
                        help="要测试的网络环境名称列表")
    parser.add_argument("--parties", nargs="+", type=int, default=[3, 5, 7, 9],
                        help="要测试的参与方数量列表")
    parser.add_argument("--repeats", type=int, default=3,
                        help="每个配置的重复测试次数")
    parser.add_argument("--output", default="network_test_results.json",
                        help="结果输出文件名")
    
    args = parser.parse_args()
    
    # 确保指定的网络环境存在
    for net in args.networks:
        if net not in NETWORK_CONDITIONS:
            print(f"错误: 未知的网络环境 '{net}'")
            print(f"可用的网络环境: {list(NETWORK_CONDITIONS.keys())}")
            return 1
    
    # 设置日志
    logger = setup_logging(filename="network_tests.log")
    
    # 更新环境变量
    os.environ['TEST_NETWORK_TYPES'] = ','.join(args.networks)
    os.environ['TEST_PARTY_COUNTS'] = ','.join(str(p) for p in args.parties)
    os.environ['TEST_REPEAT_COUNT'] = str(args.repeats)
    
    print("开始拉格朗日协议网络环境测试")
    print(f"测试网络环境: {args.networks}")
    print(f"测试参与方数量: {args.parties}")
    print(f"每个配置的重复次数: {args.repeats}")
    print(f"结果将保存到: {args.output}")
    print("")
    
    # 运行所有测试
    try:
        start_time = time.time()
        results = await run_all_tests(args.output)
        end_time = time.time()
        
        print(f"\n所有测试完成! 总运行时间: {end_time - start_time:.2f}秒")
        print(f"共测试了 {len(args.networks)} 种网络环境和 {len(args.parties)} 种参与方数量配置")
        print(f"结果保存在 {args.output} 和 network_test_results 目录")
        
        # 绘制结果图表
        plot_results(results)
        print("结果图表已生成在 network_test_results 目录")
        
        return 0
    except Exception as e:
        print(f"测试运行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
