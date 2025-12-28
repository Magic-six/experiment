#!/usr/bin/env python
"""
延迟对比实验入口脚本 - 运行不同网络延迟条件下的协议性能比较实验
"""

import asyncio
import logging
import json
import os
import time
import sys
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Any, Optional

# 添加当前目录到Python导入路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.multiplicative_group import PrimeOrderCyclicGroup
from utils.config import DEFAULT_PRIME, DEFAULT_GENERATOR, DEFAULT_X_STAR
from utils.utils import setup_logging
from protocols.protocol_extension import secure_lagrange_interpolation
from network.network_simulator import NetworkCondition

# 设置日志
logger = logging.getLogger('lagrange_protocol')

# 自定义网络条件 - 不同延迟设置
LATENCY_TEST_CONDITIONS = {
    "lan_10ms": NetworkCondition(
        name="局域网 (10ms延迟)", 
        min_delay=0.005, 
        max_delay=0.010, 
        packet_loss_rate=0.001,
        bandwidth_limit_kbps=100000  # 100 Mbps
    ),
    "lan_50ms": NetworkCondition(
        name="局域网 (50ms延迟)", 
        min_delay=0.030, 
        max_delay=0.050, 
        packet_loss_rate=0.001,
        bandwidth_limit_kbps=100000  # 100 Mbps
    ),
    "wan_50ms": NetworkCondition(
        name="广域网 (50ms延迟)", 
        min_delay=0.030, 
        max_delay=0.050, 
        packet_loss_rate=0.01,
        bandwidth_limit_kbps=10000  # 10 Mbps
    ),
    "wan_100ms": NetworkCondition(
        name="广域网 (100ms延迟)", 
        min_delay=0.080, 
        max_delay=0.100, 
        packet_loss_rate=0.01,
        bandwidth_limit_kbps=10000  # 10 Mbps
    ),
    "wan_200ms": NetworkCondition(
        name="广域网 (200ms延迟)", 
        min_delay=0.150, 
        max_delay=0.200, 
        packet_loss_rate=0.01,
        bandwidth_limit_kbps=10000  # 10 Mbps
    )
}

# 测试参与方数量
TEST_PARTY_COUNTS = [3, 4]

# 结果存储目录
RESULTS_DIR = "network_test_results/latency_experiment"
OUTPUT_FILE = "latency_comparison_results.json"

async def run_latency_test(
    party_count: int, 
    network_key: str,
    repeat_count: int = 3
) -> Dict[str, Any]:
    """
    在特定延迟条件下运行测试
    
    Args:
        party_count: 参与方数量
        network_key: 网络配置键名
        repeat_count: 重复测试次数
        
    Returns:
        测试结果统计
    """
    network_condition = LATENCY_TEST_CONDITIONS[network_key]
    logger.info(f"开始延迟测试: 参与方数量={party_count}, 网络环境={network_condition.name}")
    
    # 准备数据点
    points = [(i, i**2) for i in range(1, party_count+1)]
    
    # 存储多次测试结果
    run_times = []
    success_rates = []
    send_data_sizes = []
    recv_data_sizes = []
    compute_times = []
    
    # 重复测试多次以获得可靠结果
    for i in range(repeat_count):
        try:
            # 通过环境变量设置网络模拟参数
            os.environ['USE_NETWORK_SIMULATION'] = 'True'
            os.environ['NETWORK_TYPE'] = network_key
            os.environ['CUSTOM_MIN_DELAY'] = str(network_condition.min_delay)
            os.environ['CUSTOM_MAX_DELAY'] = str(network_condition.max_delay)
            os.environ['CUSTOM_PACKET_LOSS'] = str(network_condition.packet_loss_rate)
            os.environ['CUSTOM_BANDWIDTH'] = str(network_condition.bandwidth_limit_kbps)
            
            start_time = time.time()
            
            # 运行插值协议
            result = await secure_lagrange_interpolation(
                points, 
                DEFAULT_X_STAR,
                DEFAULT_PRIME,
                DEFAULT_GENERATOR
            )
            
            end_time = time.time()
            run_time = end_time - start_time
            
            # 收集结果
            run_times.append(run_time)
            success_rates.append(1.0)  # 成功完成
            
            # 通信统计数据从环境变量中获取
            if 'TOTAL_SEND_BYTES' in os.environ:
                send_data_sizes.append(int(os.environ.get('TOTAL_SEND_BYTES', '0')))
            if 'TOTAL_RECV_BYTES' in os.environ:
                recv_data_sizes.append(int(os.environ.get('TOTAL_RECV_BYTES', '0')))
            if 'MAX_COMPUTE_TIME' in os.environ:
                compute_times.append(float(os.environ.get('MAX_COMPUTE_TIME', '0')))
                
            logger.info(f"测试 {i+1}/{repeat_count} 完成: 运行时间={run_time:.2f}秒")
            
        except Exception as e:
            logger.error(f"测试 {i+1}/{repeat_count} 失败: {str(e)}")
            # 记录失败
            run_times.append(None)
            success_rates.append(0.0)
            send_data_sizes.append(0)
            recv_data_sizes.append(0)
            compute_times.append(0)
    
    # 计算统计结果
    success_rate = sum(sr for sr in success_rates if sr is not None) / repeat_count
    valid_run_times = [rt for rt in run_times if rt is not None]
    valid_compute_times = [ct for ct in compute_times if ct is not None]
    
    result = {
        "party_count": party_count,
        "network_key": network_key,
        "network_name": network_condition.name,
        "min_delay": network_condition.min_delay * 1000,  # 转换为ms
        "max_delay": network_condition.max_delay * 1000,  # 转换为ms
        "avg_run_time": sum(valid_run_times) / len(valid_run_times) if valid_run_times else None,
        "min_run_time": min(valid_run_times) if valid_run_times else None,
        "max_run_time": max(valid_run_times) if valid_run_times else None,
        "avg_compute_time": sum(valid_compute_times) / len(valid_compute_times) if valid_compute_times else None,
        "success_rate": success_rate,
        "avg_send_data_size": sum(send_data_sizes) / len(send_data_sizes) if send_data_sizes else 0,
        "avg_recv_data_size": sum(recv_data_sizes) / len(recv_data_sizes) if recv_data_sizes else 0,
    }
    
    logger.info(f"延迟测试结果: {result}")
    return result

async def run_all_latency_tests() -> List[Dict[str, Any]]:
    """
    运行所有延迟测试场景
        
    Returns:
        测试结果列表
    """
    # 创建结果目录
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    all_results = []
    
    # 对每种延迟条件和参与方数量进行测试
    for network_key in LATENCY_TEST_CONDITIONS.keys():
        for party_count in TEST_PARTY_COUNTS:
            result = await run_latency_test(party_count, network_key)
            all_results.append(result)
            
            # 保存中间结果
            output_path = os.path.join(RESULTS_DIR, OUTPUT_FILE)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            logger.info(f"中间结果已保存至 {output_path}")
    
    return all_results

def plot_latency_results(results: List[Dict[str, Any]], prefix: str = "latency_") -> None:
    """
    绘制延迟测试结果图表
    
    Args:
        results: 测试结果列表
        prefix: 输出文件名前缀
    """
    # 创建结果目录
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # 配置字体以支持中文
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'FangSong']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 按网络类型分组结果
    network_keys = list(set(r["network_key"] for r in results))
    party_counts = sorted(list(set(r["party_count"] for r in results)))
    
    # 1. 绘制运行时间对比图 - 按参与方数量分组
    plt.figure(figsize=(14, 10))
    
    # 为不同的参与方数量创建子图
    fig, axes = plt.subplots(len(party_counts), 1, figsize=(12, 4*len(party_counts)))
    
    for i, party_count in enumerate(party_counts):
        ax = axes[i] if len(party_counts) > 1 else axes
        
        # 提取当前参与方数量的数据
        network_keys_sorted = []
        run_times = []
        network_names = []
        
        for network_key in LATENCY_TEST_CONDITIONS.keys():
            for r in results:
                if r["party_count"] == party_count and r["network_key"] == network_key:
                    network_keys_sorted.append(network_key)
                    run_times.append(r["avg_run_time"] if r["avg_run_time"] else 0)
                    network_names.append(r["network_name"])
                    break
        
        # 绘制条形图
        bars = ax.bar(network_names, run_times)
        
        # 在条形图上标注数值
        for bar, value in zip(bars, run_times):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{value:.2f}s', ha='center', va='bottom', fontsize=9)
        
        ax.set_title(f'参与方数量: {party_count}')
        ax.set_ylabel('平均运行时间 (秒)')
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # 横轴标签旋转以避免重叠
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
    
    plt.suptitle('不同延迟条件下协议运行时间对比', fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # 为总标题留出空间
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}runtime_by_parties.png'))
    
    # 2. LAN vs WAN 比较图
    plt.figure(figsize=(14, 8))
    
    # 提取LAN和WAN数据
    lan_data = []
    wan_data = []
    
    for party_count in party_counts:
        lan_50ms = None
        wan_50ms = None
        wan_100ms = None
        
        for r in results:
            if r["party_count"] == party_count:
                if r["network_key"] == "lan_50ms":
                    lan_50ms = r["avg_run_time"] if r["avg_run_time"] else 0
                elif r["network_key"] == "wan_50ms":
                    wan_50ms = r["avg_run_time"] if r["avg_run_time"] else 0
                elif r["network_key"] == "wan_100ms":
                    wan_100ms = r["avg_run_time"] if r["avg_run_time"] else 0
        
        if lan_50ms is not None and wan_50ms is not None and wan_100ms is not None:
            lan_data.append(lan_50ms)
            wan_data.append((wan_50ms, wan_100ms))
    
    # 绘制比较图
    x = np.arange(len(party_counts))
    width = 0.25
    
    fig, ax = plt.subplots(figsize=(14, 8))
    rects1 = ax.bar(x - width, lan_data, width, label='局域网 (50ms延迟)', color='royalblue')
    rects2 = ax.bar(x, [w[0] for w in wan_data], width, label='广域网 (50ms延迟)', color='forestgreen')
    rects3 = ax.bar(x + width, [w[1] for w in wan_data], width, label='广域网 (100ms延迟)', color='mediumpurple')
    
    # 添加数据标签
    def add_labels(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3点垂直偏移
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)
    
    add_labels(rects1)
    add_labels(rects2)
    add_labels(rects3)
    
    # 设置图表元素
    ax.set_xlabel('参与方数量')
    ax.set_ylabel('平均运行时间 (秒)')
    ax.set_title('局域网与广域网环境下的协议运行时间对比')
    ax.set_xticks(x)
    ax.set_xticklabels(party_counts)
    # 将图例放在右侧的空白区域
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.grid(True, linestyle='--', alpha=0.7, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}lan_vs_wan_comparison.png'), bbox_inches='tight')

async def main():
    """主函数"""
    # 设置日志
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(filename='latency_experiment.log', log_dir=log_dir)
    
    print("\n" + "=" * 80)
    print("欢迎使用延迟对比实验系统")
    print("本实验将在模拟的LAN和WAN环境下（设置具体的延迟，如50ms/100ms）进行对比")
    print("=" * 80)
    
    print("\n实验配置:")
    print("- 网络环境: 局域网(10ms/50ms), 广域网(50ms/100ms/200ms)")
    print("- 参与方数量: 3, 5, 7, 9")
    print("- 每个配置重复3次以确保结果可靠")
    
    print("\n开始运行实验...\n")
    
    try:
        # 运行所有测试
        results = await run_all_latency_tests()
        
        # 绘制结果图表
        plot_latency_results(results)
        
        # 打印实验结果摘要
        print("\n实验完成! 结果摘要:")
        for r in results:
            print(f"- 参与方数量: {r['party_count']}, 环境: {r['network_name']}, 运行时间: {r['avg_run_time']:.2f}秒")
        
        # 指出结果位置
        print(f"\n详细结果已保存至: {RESULTS_DIR}")
        print(f"- 原始数据: {os.path.join(RESULTS_DIR, OUTPUT_FILE)}")
        print(f"- 结果图表: {RESULTS_DIR}/*.png")
        
        return results
    except Exception as e:
        print(f"\n实验过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
