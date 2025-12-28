"""
高性能网络测试运行脚本 - 运行不同网络环境下的拉格朗日协议测试并生成比较报告
具有更高效的并行执行和报告生成能力
"""

import asyncio
import argparse
import os
import time
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import concurrent.futures
from contextlib import suppress

# 导入必要的模块
from network_test import TEST_NETWORK_TYPES, TEST_PARTY_COUNTS, RESULTS_DIR
from utils import setup_logging
from network_simulator import NETWORK_CONDITIONS
from config import MAX_PARTIES, MIN_PARTIES

# 设置默认值
DEFAULT_TIMEOUT = 300  # 每个测试的超时时间（秒）
DEFAULT_NETWORKS = ["local", "lan", "wan", "iot"]
DEFAULT_PARTIES = [3, 5]
DEFAULT_REPEATS = 2
DEFAULT_OUTPUT = "network_test_results_optimized.json"

# 设置性能优化选项
OPTIMIZE_FOR_SPEED = True  # 启用速度优化
ENABLE_COMPRESSION = True  # 启用数据压缩
PARALLEL_EXECUTION = True  # 启用并行执行
MAX_PARALLEL_TASKS = 2    # 最大并行任务数

async def run_single_test(party_count: int, network_type: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    运行单个网络测试
    
    Args:
        party_count: 参与方数量
        network_type: 网络类型
        timeout: 测试超时时间（秒）
        
    Returns:
        测试结果
    """
    # 设置环境变量
    os.environ['USE_NETWORK_SIMULATION'] = 'true'
    os.environ['NETWORK_TYPE'] = network_type
    
    # 如果启用了性能优化，设置相应环境变量
    if OPTIMIZE_FOR_SPEED:
        os.environ['OPTIMIZE_FOR_SPEED'] = 'true'
    if ENABLE_COMPRESSION:
        os.environ['ENABLE_COMPRESSION'] = 'true'
    
    # 记录开始时间
    start_time = time.time()
    
    # 导入测试模块（动态导入避免循环引用）
    from network_test import run_network_test
    
    try:
        # 使用超时运行测试
        result = await asyncio.wait_for(
            run_network_test(party_count, network_type),
            timeout=timeout
        )
        # 如果成功，记录运行时间
        run_time = time.time() - start_time
        result['actual_run_time'] = run_time
        result['success'] = True
        return result
    except asyncio.TimeoutError:
        # 测试超时
        print(f"测试超时: 参与方数量={party_count}, 网络类型={network_type}")
        return {
            'party_count': party_count,
            'network_type': network_type,
            'success': False,
            'error': 'timeout',
            'actual_run_time': timeout
        }
    except Exception as e:
        # 其他错误
        print(f"测试失败: 参与方数量={party_count}, 网络类型={network_type}, 错误: {e}")
        return {
            'party_count': party_count, 
            'network_type': network_type,
            'success': False,
            'error': str(e),
            'actual_run_time': time.time() - start_time
        }

async def run_tests_batch(
    test_configs: List[Tuple[int, str]], 
    repeats: int
) -> List[Dict[str, Any]]:
    """
    批量运行测试配置
    
    Args:
        test_configs: 测试配置列表，每项为(参与方数量，网络类型)
        repeats: 每个配置的重复次数
        
    Returns:
        测试结果列表
    """
    results = []
    
    # 计算总测试数量
    total_tests = len(test_configs) * repeats
    completed = 0
    
    # 创建包含所有测试的任务列表
    all_tasks = []
    for party_count, network_type in test_configs:
        for r in range(repeats):
            all_tasks.append((party_count, network_type, r+1))
    
    # 根据是否启用并行执行选择不同策略
    if PARALLEL_EXECUTION:
        # 创建并行任务组
        task_groups = []
        current_group = []
        
        for task in all_tasks:
            current_group.append(task)
            if len(current_group) >= MAX_PARALLEL_TASKS:
                task_groups.append(current_group)
                current_group = []
        
        if current_group:  # 添加剩余任务
            task_groups.append(current_group)
        
        # 按组执行任务
        for group_idx, group in enumerate(task_groups):
            print(f"执行任务组 {group_idx+1}/{len(task_groups)} - {len(group)}个任务")
            tasks = []
            
            for party_count, network_type, repeat_num in group:
                print(f"  启动测试: 参与方数量={party_count}, 网络类型={network_type}, 重复次数={repeat_num}/{repeats}")
                task = asyncio.create_task(run_single_test(party_count, network_type))
                tasks.append((party_count, network_type, repeat_num, task))
            
            # 等待所有任务完成
            for party_count, network_type, repeat_num, task in tasks:
                try:
                    result = await task
                    results.append(result)
                    completed += 1
                    print(f"  完成测试: 参与方数量={party_count}, 网络类型={network_type}, "
                          f"重复次数={repeat_num}/{repeats} ({completed}/{total_tests})")
                except Exception as e:
                    print(f"  测试失败: 参与方数量={party_count}, 网络类型={network_type}, 错误: {e}")
                    results.append({
                        'party_count': party_count,
                        'network_type': network_type,
                        'success': False,
                        'error': str(e)
                    })
                    completed += 1
    else:
        # 顺序执行所有任务
        for party_count, network_type, repeat_num in all_tasks:
            print(f"执行测试: 参与方数量={party_count}, 网络类型={network_type}, "
                  f"重复次数={repeat_num}/{repeats} ({completed+1}/{total_tests})")
            result = await run_single_test(party_count, network_type)
            results.append(result)
            completed += 1
    
    return results

async def process_results(raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    处理原始测试结果，按配置聚合并计算统计数据
    
    Args:
        raw_results: 原始测试结果列表
        
    Returns:
        聚合后的结果列表
    """
    # 按配置分组结果
    grouped_results = {}
    
    for result in raw_results:
        if not result.get('success', False):
            continue
            
        party_count = result['party_count']
        network_type = result['network_type']
        key = f"{party_count}_{network_type}"
        
        if key not in grouped_results:
            grouped_results[key] = {
                'party_count': party_count,
                'network_type': network_type,
                'network_condition': str(NETWORK_CONDITIONS[network_type]),
                'results': []
            }
        
        grouped_results[key]['results'].append(result)
    
    # 计算聚合统计
    aggregated_results = []
    for group_data in grouped_results.values():
        results = group_data['results']
        
        if not results:
            continue
            
        successful_results = [r for r in results if r.get('success', False)]
        success_rate = len(successful_results) / len(results) if results else 0
        
        if not successful_results:
            continue
            
        # 计算统计信息
        run_times = [r.get('run_time', r.get('actual_run_time', 0)) for r in successful_results]
        send_data_sizes = [r.get('send_data_size', 0) for r in successful_results]
        recv_data_sizes = [r.get('recv_data_size', 0) for r in successful_results]
        
        aggregated_result = {
            'party_count': group_data['party_count'],
            'network_type': group_data['network_type'],
            'network_condition': group_data['network_condition'],
            'avg_run_time': sum(run_times) / len(run_times),
            'min_run_time': min(run_times),
            'max_run_time': max(run_times),
            'success_rate': success_rate,
            'avg_send_data_size': sum(send_data_sizes) / len(send_data_sizes),
            'avg_recv_data_size': sum(recv_data_sizes) / len(recv_data_sizes)
        }
        
        aggregated_results.append(aggregated_result)
    
    # 按参与方数量和网络类型排序
    return sorted(aggregated_results, key=lambda r: (r['party_count'], r['network_type']))

async def main():
    """主函数"""
    # 声明全局变量
    global PARALLEL_EXECUTION, MAX_PARALLEL_TASKS, OPTIMIZE_FOR_SPEED, ENABLE_COMPRESSION
    
    parser = argparse.ArgumentParser(description="高性能拉格朗日协议网络环境测试")
    parser.add_argument("--networks", nargs="+", default=DEFAULT_NETWORKS,
                        help=f"要测试的网络环境名称列表 (可选: {', '.join(NETWORK_CONDITIONS.keys())})")
    parser.add_argument("--parties", nargs="+", type=int, default=DEFAULT_PARTIES,
                        help=f"要测试的参与方数量列表 (范围: {MIN_PARTIES}-{MAX_PARTIES})")
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS,
                        help="每个配置的重复测试次数")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help="结果输出文件名")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="每个测试的超时时间（秒）")
    parser.add_argument("--parallel", action="store_true", default=PARALLEL_EXECUTION,
                        help="启用并行执行")
    parser.add_argument("--max-parallel", type=int, default=MAX_PARALLEL_TASKS,
                        help="最大并行任务数")
    parser.add_argument("--optimize-speed", action="store_true", default=OPTIMIZE_FOR_SPEED,
                        help="启用速度优化")
    parser.add_argument("--compression", action="store_true", default=ENABLE_COMPRESSION,
                        help="启用数据压缩")
    
    args = parser.parse_args()
    
    # 更新全局配置
    PARALLEL_EXECUTION = args.parallel
    MAX_PARALLEL_TASKS = args.max_parallel
    OPTIMIZE_FOR_SPEED = args.optimize_speed
    ENABLE_COMPRESSION = args.compression
    
    # 确保指定的网络环境存在
    for net in args.networks:
        if net not in NETWORK_CONDITIONS:
            print(f"错误: 未知的网络环境 '{net}'")
            print(f"可用的网络环境: {list(NETWORK_CONDITIONS.keys())}")
            return 1
    
    # 确保参与方数量在有效范围内
    for party in args.parties:
        if not (MIN_PARTIES <= party <= MAX_PARTIES):
            print(f"错误: 无效的参与方数量 '{party}', 必须在 {MIN_PARTIES}-{MAX_PARTIES} 范围内")
            return 1
    
    # 设置日志
    logger = setup_logging(filename="optimized_network_tests.log")
    
    print("=== 拉格朗日协议网络环境优化测试 ===")
    print(f"测试网络环境: {args.networks}")
    print(f"测试参与方数量: {args.parties}")
    print(f"每个配置的重复次数: {args.repeats}")
    print(f"超时时间: {args.timeout}秒")
    print(f"启用并行执行: {PARALLEL_EXECUTION}")
    if PARALLEL_EXECUTION:
        print(f"最大并行任务数: {MAX_PARALLEL_TASKS}")
    print(f"启用速度优化: {OPTIMIZE_FOR_SPEED}")
    print(f"启用数据压缩: {ENABLE_COMPRESSION}")
    print(f"结果将保存到: {args.output}")
    print("")
    
    # 确保结果目录存在
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    
    # 生成测试配置
    test_configs = []
    for party_count in args.parties:
        for network_type in args.networks:
            test_configs.append((party_count, network_type))
    
    try:
        start_time = time.time()
        print(f"开始执行 {len(test_configs)} 种配置, 每种配置重复 {args.repeats} 次, 共 {len(test_configs) * args.repeats} 次测试")
        
        # 执行测试
        raw_results = await run_tests_batch(test_configs, args.repeats)
        
        # 处理结果
        results = await process_results(raw_results)
        
        # 保存结果
        output_path = os.path.join(RESULTS_DIR, args.output)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # 绘制结果图表
        print("正在生成结果图表...")
        try:
            # 动态导入以避免模块依赖问题
            from network_test import plot_results
            plot_results(results)
            print("结果图表已生成")
        except ImportError:
            print("警告: 无法导入绘图模块。请确保已安装matplotlib。")
        except Exception as e:
            print(f"生成图表时出错: {e}")
        
        end_time = time.time()
        print(f"\n所有测试完成! 总运行时间: {end_time - start_time:.2f}秒")
        print(f"结果保存在: {output_path}")
        
        return 0
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n测试运行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # 使用uvloop加速（如果可用）
    with suppress(ImportError):
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    sys.exit(asyncio.run(main()))
