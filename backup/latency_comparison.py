"""
延迟比较实验模块 - 测试不同延迟条件下协议的运行时间和通信效率
"""

import time
import asyncio
import logging
import json
import os
import platform
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

from multiplicative_group import PrimeOrderCyclicGroup
from utils import setup_logging
from protocol_extension import secure_lagrange_interpolation
from network_simulator import NetworkCondition
from config import DEFAULT_PRIME, DEFAULT_GENERATOR, DEFAULT_X_STAR

# 设置日志
logger = logging.getLogger('lagrange_protocol')

# 配置matplotlib支持中文
def configure_matplotlib_fonts():
    """配置matplotlib以支持中文字体"""
    if platform.system() == 'Windows':
        # 尝试使用多种Windows中文字体
        chinese_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'FangSong']
        font_found = False
        
        for font_name in chinese_fonts:
            try:
                plt.rcParams['font.sans-serif'] = [font_name]
                plt.rcParams['axes.unicode_minus'] = False
                font_found = True
                break
            except:
                continue
                
        if not font_found:
            print("警告: 未找到中文字体，将使用默认字体")
    """配置matplotlib以支持中文字体"""
    if platform.system() == 'Windows':
        # 尝试使用多种Windows中文字体
        chinese_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'FangSong']
        font_found = False
        
        for font_name in chinese_fonts:
            try:
                plt.rcParams['font.sans-serif'] = [font_name]
                font_found = True
                break
            except:
                continue
                
        if not font_found:
            try:
                # 回退到微软雅黑
                font_path = 'C:/Windows/Fonts/msyh.ttc'  # 微软雅黑字体路径
                font_properties = matplotlib.font_manager.FontProperties(fname=font_path)
                plt.rcParams['font.family'] = font_properties.get_name()
            except:
                print("警告: 未找到中文字体，将使用默认字体")
    elif platform.system() == 'Darwin':  # macOS
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
    else:  # Linux
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
    
    plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号

# 配置字体
try:
    configure_matplotlib_fonts()
except Exception as e:
    print(f"警告: 配置中文字体失败: {e}，将使用默认字体")

# 测试配置 - 自定义网络延迟设置
CUSTOM_NETWORK_CONDITIONS = {
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
TEST_PARTY_COUNTS = [3, 5, 7, 9]

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
    network_condition = CUSTOM_NETWORK_CONDITIONS[network_key]
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
        "communication_efficiency": sum(valid_run_times) / sum(send_data_sizes) if valid_run_times and sum(send_data_sizes) > 0 else None
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
    for network_key in CUSTOM_NETWORK_CONDITIONS.keys():
        for party_count in TEST_PARTY_COUNTS:
            result = await run_latency_test(party_count, network_key)
            all_results.append(result)
            
            # 保存中间结果
            output_path = os.path.join(RESULTS_DIR, OUTPUT_FILE)
            with open(output_path, 'w') as f:
                json.dump(all_results, f, indent=2)
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
    
    # 尝试再次配置字体
    try:
        configure_matplotlib_fonts()
    except:
        pass
    
    # 按网络类型分组结果
    network_keys = list(set(r["network_key"] for r in results))
    party_counts = sorted(list(set(r["party_count"] for r in results)))
    
    # 1. 绘制运行时间对比图
    plt.figure(figsize=(14, 10))
    
    # 为不同的参与方数量创建子图
    fig, axes = plt.subplots(len(party_counts), 1, figsize=(12, 4*len(party_counts)))
    
    for i, party_count in enumerate(party_counts):
        ax = axes[i] if len(party_counts) > 1 else axes
        
        # 提取当前参与方数量的数据
        network_keys_sorted = []
        run_times = []
        network_names = []
        
        for network_key in CUSTOM_NETWORK_CONDITIONS.keys():
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
    
    # 2. 绘制通信效率图 - 按参与方数量分组
    plt.figure(figsize=(14, 10))
    
    # 为不同的网络类型创建子图
    fig, axes = plt.subplots(len(network_keys), 1, figsize=(12, 4*len(network_keys)))
    
    for i, network_key in enumerate(network_keys):
        ax = axes[i] if len(network_keys) > 1 else axes
        
        # 提取数据
        x_values = []
        run_times = []
        data_sizes = []
        network_name = ""
        
        for party_count in party_counts:
            for r in results:
                if r["network_key"] == network_key and r["party_count"] == party_count:
                    x_values.append(party_count)
                    run_times.append(r["avg_run_time"] if r["avg_run_time"] else 0)
                    data_sizes.append(r["avg_send_data_size"] / 1024)  # 转为KB
                    network_name = r["network_name"]
                    break
        
        # 创建双Y轴图
        color1, color2 = 'tab:blue', 'tab:red'
        ax.set_xlabel('参与方数量')
        ax.set_ylabel('平均运行时间 (秒)', color=color1)
        ax.plot(x_values, run_times, marker='o', color=color1, label='运行时间')
        ax.tick_params(axis='y', labelcolor=color1)
        
        # 第二个Y轴 - 数据量
        ax2 = ax.twinx()
        ax2.set_ylabel('发送数据量 (KB)', color=color2)
        ax2.plot(x_values, data_sizes, marker='s', color=color2, label='数据量')
        ax2.tick_params(axis='y', labelcolor=color2)
        
        # 设置标题和网格
        ax.set_title(f'网络环境: {network_name}')
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 添加图例
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.suptitle('不同延迟条件下运行时间与数据量关系', fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # 为总标题留出空间
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}runtime_vs_datasize.png'))
    
    # 3. LAN vs WAN 比较图
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
    rects1 = ax.bar(x - width, lan_data, width, label='局域网 (50ms延迟)')
    rects2 = ax.bar(x, [w[0] for w in wan_data], width, label='广域网 (50ms延迟)')
    rects3 = ax.bar(x + width, [w[1] for w in wan_data], width, label='广域网 (100ms延迟)')
    
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
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}lan_vs_wan_comparison.png'))
    
    # 4. 计算时间与通信时间对比
    plt.figure(figsize=(14, 8))
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    for net_idx, network_key in enumerate(["lan_50ms", "wan_50ms", "wan_100ms"]):
        compute_times = []
        network_times = []
        
        for party_count in party_counts:
            for r in results:
                if r["network_key"] == network_key and r["party_count"] == party_count:
                    if r["avg_compute_time"] is not None and r["avg_run_time"] is not None:
                        compute_times.append(r["avg_compute_time"])
                        network_times.append(r["avg_run_time"] - r["avg_compute_time"])
                    break
        
        if compute_times and network_times:
            width = 0.25
            x = np.arange(len(party_counts))
            offset = (net_idx - 1) * width
            
            # 堆叠条形图
            p1 = ax.bar(x + offset, compute_times, width, label=f'计算时间 ({CUSTOM_NETWORK_CONDITIONS[network_key].name})' 
                        if net_idx == 0 else "_nolegend_")
            p2 = ax.bar(x + offset, network_times, width, bottom=compute_times, 
                       label=f'通信时间 ({CUSTOM_NETWORK_CONDITIONS[network_key].name})'
                        if net_idx == 0 else "_nolegend_")
            
            # 添加总时间标签
            for i, (comp, net) in enumerate(zip(compute_times, network_times)):
                total = comp + net
                ax.text(x[i] + offset, total + 0.05, f'{total:.2f}s',
                        ha='center', va='bottom', fontsize=8)
    
    # 设置图表
    ax.set_xlabel('参与方数量')
    ax.set_ylabel('时间 (秒)')
    ax.set_title('不同网络环境下的计算时间与通信时间占比')
    ax.set_xticks(x)
    ax.set_xticklabels(party_counts)
    
    # 创建自定义图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='tab:blue', label='计算时间'),
        Patch(facecolor='tab:orange', label='通信时间'),
        Patch(facecolor='white', edgecolor='black', label='局域网 (50ms延迟)'),
        Patch(facecolor='white', edgecolor='black', label='广域网 (50ms延迟)'),
        Patch(facecolor='white', edgecolor='black', label='广域网 (100ms延迟)')
    ]
    ax.legend(handles=legend_elements, loc='upper left')
    
    ax.grid(True, linestyle='--', alpha=0.7, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, f'{prefix}compute_vs_network_time.png'))

async def main():
    """主函数"""
    # 设置日志
    setup_logging(filename='latency_test.log')
    
    logger.info("开始网络延迟对比测试")
    
    # 运行所有测试
    results = await run_all_latency_tests()
    
    # 绘制结果图表
    plot_latency_results(results)
    
    logger.info("网络延迟对比测试完成")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
