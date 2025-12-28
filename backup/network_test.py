"""
网络环境测试模块 - 测试协议在不同网络环境下的性能
"""

import time
import asyncio
import logging
import json
import os
import platform
from typing import List, Dict, Any, Tuple, Optional
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# 配置matplotlib支持中文
def configure_matplotlib_fonts():
    """配置matplotlib以支持中文字体"""
    if platform.system() == 'Windows':
        # Windows系统使用微软雅黑
        font_path = 'C:/Windows/Fonts/msyh.ttc'  # 微软雅黑字体路径
        font_properties = matplotlib.font_manager.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = font_properties.get_name()
    elif platform.system() == 'Darwin':  # macOS
        plt.rcParams['font.family'] = 'Arial Unicode MS'
    else:  # Linux
        plt.rcParams['font.family'] = 'WenQuanYi Micro Hei'
    
    plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号

# 配置字体
try:
    configure_matplotlib_fonts()
except Exception as e:
    print(f"警告: 配置中文字体失败: {e}，将使用默认字体")

from multiplicative_group import PrimeOrderCyclicGroup
from utils import setup_logging, generate_triples
from protocol_extension import secure_lagrange_interpolation
from network_simulator import NETWORK_CONDITIONS
from config import DEFAULT_PRIME, DEFAULT_GENERATOR, DEFAULT_X_STAR

# 设置日志
logger = logging.getLogger('lagrange_protocol')

# 测试配置
TEST_NETWORK_TYPES = [
    "local", 
    "lan", 
    "wan", 
    "poor_wan", 
    "mobile_4g", 
    "iot", 
    "satellite"
]

TEST_PARTY_COUNTS = [3, 5, 7, 9]

RESULTS_DIR = "network_test_results"

async def run_network_test(
    party_count: int, 
    network_type: str, 
    repeat_count: int = 3
) -> Dict[str, Any]:
    """
    在特定网络条件下运行测试
    
    Args:
        party_count: 参与方数量
        network_type: 网络类型
        repeat_count: 重复测试次数
        
    Returns:
        测试结果统计
    """
    logger.info(f"开始网络测试: 参与方数量={party_count}, 网络类型={network_type}")
    
    # 准备数据点
    points = [(i, i**2) for i in range(1, party_count+1)]
    
    # 存储多次测试结果
    run_times = []
    success_rates = []
    send_data_sizes = []
    recv_data_sizes = []
    
    # 重复测试多次以获得可靠结果
    for i in range(repeat_count):
        try:
            # 替换掉原始的participant模块，使用支持网络模拟的版本
            # 这里通过设置环境变量告诉协议使用增强版的参与方
            os.environ['USE_NETWORK_SIMULATION'] = 'True'
            os.environ['NETWORK_TYPE'] = network_type
            
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
            
            # 通信统计数据需要从增强参与方中收集
            # 这里假设我们会在secure_lagrange_interpolation函数中记录这些信息
            # 并通过环境变量返回
            if 'TOTAL_SEND_BYTES' in os.environ:
                send_data_sizes.append(int(os.environ.get('TOTAL_SEND_BYTES', '0')))
            if 'TOTAL_RECV_BYTES' in os.environ:
                recv_data_sizes.append(int(os.environ.get('TOTAL_RECV_BYTES', '0')))
                
            logger.info(f"测试 {i+1}/{repeat_count} 完成: 运行时间={run_time:.2f}秒")
            
        except Exception as e:
            logger.error(f"测试 {i+1}/{repeat_count} 失败: {str(e)}")
            # 记录失败
            run_times.append(None)
            success_rates.append(0.0)
            send_data_sizes.append(0)
            recv_data_sizes.append(0)
    
    # 计算统计结果
    success_rate = sum(sr for sr in success_rates if sr is not None) / repeat_count
    valid_run_times = [rt for rt in run_times if rt is not None]
    
    result = {
        "party_count": party_count,
        "network_type": network_type,
        "network_condition": str(NETWORK_CONDITIONS[network_type]),
        "avg_run_time": sum(valid_run_times) / len(valid_run_times) if valid_run_times else None,
        "min_run_time": min(valid_run_times) if valid_run_times else None,
        "max_run_time": max(valid_run_times) if valid_run_times else None,
        "success_rate": success_rate,
        "avg_send_data_size": sum(send_data_sizes) / len(send_data_sizes) if send_data_sizes else 0,
        "avg_recv_data_size": sum(recv_data_sizes) / len(recv_data_sizes) if recv_data_sizes else 0,
    }
    
    logger.info(f"网络测试结果: {result}")
    return result

async def run_all_tests(output_file: str = "network_test_results.json") -> List[Dict[str, Any]]:
    """
    运行所有测试场景
    
    Args:
        output_file: 结果输出文件
        
    Returns:
        测试结果列表
    """
    # 创建结果目录
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    all_results = []
    
    # 对每种网络条件和参与方数量进行测试
    for network_type in TEST_NETWORK_TYPES:
        for party_count in TEST_PARTY_COUNTS:
            result = await run_network_test(party_count, network_type)
            all_results.append(result)
            
            # 保存中间结果
            with open(os.path.join(RESULTS_DIR, output_file), 'w') as f:
                json.dump(all_results, f, indent=2)
    
    return all_results

def plot_results(results: List[Dict[str, Any]], prefix: str = "") -> None:
    """
    绘制测试结果图表
    
    Args:
        results: 测试结果列表
        prefix: 输出文件名前缀（可选）
    """
    # 创建结果目录
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # 尝试再次配置字体
    try:
        configure_matplotlib_fonts()
    except:
        pass
    
    # 按网络类型分组结果
    network_types = list(set(r["network_type"] for r in results))
    party_counts = sorted(list(set(r["party_count"] for r in results)))
    
    # 1. 绘制运行时间图
    plt.figure(figsize=(12, 8))
    
    for net_type in network_types:
        # 提取当前网络类型的数据
        times = []
        for party_count in party_counts:
            for r in results:
                if r["network_type"] == net_type and r["party_count"] == party_count:
                    times.append(r["avg_run_time"] if r["avg_run_time"] else 0)
                    break
            else:
                times.append(0)  # 如果没找到匹配数据
                
        plt.plot(party_counts, times, marker='o', label=NETWORK_CONDITIONS[net_type].name)
    
    plt.xlabel('参与方数量')
    plt.ylabel('平均运行时间 (秒)')
    plt.title('不同网络条件下协议运行时间')
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}runtime_comparison.png'))
    
    # 2. 绘制成功率图
    plt.figure(figsize=(12, 8))
    
    for net_type in network_types:
        rates = []
        for party_count in party_counts:
            for r in results:
                if r["network_type"] == net_type and r["party_count"] == party_count:
                    rates.append(r["success_rate"])
                    break
            else:
                rates.append(0)
                
        plt.plot(party_counts, rates, marker='o', label=NETWORK_CONDITIONS[net_type].name)
    
    plt.xlabel('参与方数量')
    plt.ylabel('协议成功率')
    plt.title('不同网络条件下协议成功率')
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}success_rate_comparison.png'))
    
    # 3. 绘制通信量图
    plt.figure(figsize=(12, 8))
    
    for net_type in network_types:
        data_sizes = []
        for party_count in party_counts:
            for r in results:
                if r["network_type"] == net_type and r["party_count"] == party_count:
                    data_sizes.append(r["avg_send_data_size"] / 1024)  # 转换为KB
                    break
            else:
                data_sizes.append(0)
                
        plt.plot(party_counts, data_sizes, marker='o', label=NETWORK_CONDITIONS[net_type].name)
    
    plt.xlabel('参与方数量')
    plt.ylabel('平均发送数据量 (KB)')
    plt.title('不同网络条件下协议通信量')
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}communication_comparison.png'))
    
    # 4. 绘制比较条形图
    plt.figure(figsize=(14, 10))
    
    # 每个网络类型分一个子图
    fig, axes = plt.subplots(len(network_types), 1, figsize=(12, 3*len(network_types)))
    
    for i, net_type in enumerate(network_types):
        ax = axes[i] if len(network_types) > 1 else axes
        
        # 获取数据
        times = []
        for party_count in party_counts:
            for r in results:
                if r["network_type"] == net_type and r["party_count"] == party_count:
                    times.append(r["avg_run_time"] if r["avg_run_time"] else 0)
                    break
            else:
                times.append(0)
        
        # 绘制条形图
        ax.bar(party_counts, times)
        ax.set_title(f'网络环境: {NETWORK_CONDITIONS[net_type].name}')
        ax.set_xlabel('参与方数量')
        ax.set_ylabel('平均运行时间 (秒)')
        ax.grid(True, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}network_runtime_detail.png'))
    
    # 5. 绘制热图
    plt.figure(figsize=(10, 8))
    
    # 准备热图数据
    heatmap_data = np.zeros((len(network_types), len(party_counts)))
    
    for i, net_type in enumerate(network_types):
        for j, party_count in enumerate(party_counts):
            for r in results:
                if r["network_type"] == net_type and r["party_count"] == party_count:
                    heatmap_data[i, j] = r["avg_run_time"] if r["avg_run_time"] else 0
                    break
    
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(heatmap_data)
    
    # 设置坐标轴标签
    ax.set_xticks(np.arange(len(party_counts)))
    ax.set_yticks(np.arange(len(network_types)))
    ax.set_xticklabels(party_counts)
    ax.set_yticklabels([NETWORK_CONDITIONS[nt].name for nt in network_types])
    
    # 旋转x轴标签
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # 添加颜色条
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("运行时间 (秒)", rotation=-90, va="bottom")
    
    # 在每个单元格中显示具体数值
    for i in range(len(network_types)):
        for j in range(len(party_counts)):
            text = ax.text(j, i, f"{heatmap_data[i, j]:.2f}",
                          ha="center", va="center", color="w" if heatmap_data[i, j] > np.max(heatmap_data)/2 else "black")
    
    ax.set_title("不同网络环境和参与方数量下的运行时间热图")
    fig.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}runtime_heatmap.png'))

async def main():
    """主函数"""
    # 设置日志
    setup_logging(filename='network_test.log')
    
    logger.info("开始网络环境测试")
    
    # 运行所有测试
    results = await run_all_tests()
    
    # 绘制结果图表
    plot_results(results)
    
    logger.info("网络环境测试完成")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
