"""
运行延迟比较实验的简单脚本
"""

import asyncio
import logging
import os
import matplotlib
import matplotlib.pyplot as plt
import platform
from latency_comparison import main as run_latency_tests

def setup_matplotlib_font():
    """设置matplotlib字体以正确显示中文"""
    if platform.system() == 'Windows':
        # 尝试使用多种Windows中文字体
        chinese_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'FangSong']
        font_found = False
        
        for font_name in chinese_fonts:
            try:
                plt.rcParams['font.sans-serif'] = [font_name]
                plt.rcParams['axes.unicode_minus'] = False
                font_found = True
                print(f"使用中文字体: {font_name}")
                break
            except Exception as e:
                print(f"尝试字体 {font_name} 失败: {e}")
                continue
                
        if not font_found:
            try:
                # 尝试使用微软雅黑字体文件
                font_path = 'C:/Windows/Fonts/msyh.ttc'  # 微软雅黑字体路径
                if os.path.exists(font_path):
                    font_properties = matplotlib.font_manager.FontProperties(fname=font_path)
                    plt.rcParams['font.family'] = font_properties.get_name()
                    print("使用字体文件: msyh.ttc")
                else:
                    print("未找到微软雅黑字体文件")
            except Exception as e:
                print(f"字体配置失败: {e}")

async def main():
    """主函数"""
    print("="*50)
    print(" 开始运行延迟对比实验 ")
    print(" 测试局域网和广域网环境下的通信效率 ")
    print("="*50)
    
    # 配置中文字体
    print("\n配置中文字体...")
    setup_matplotlib_font()
    
    # 确保结果目录结构存在
    results_dir = "network_test_results"
    latency_results_dir = os.path.join(results_dir, "latency_experiment")
    original_results_dir = os.path.join(results_dir, "original_experiment")
    
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(latency_results_dir, exist_ok=True)
    os.makedirs(original_results_dir, exist_ok=True)
    
    print(f"\n已创建结果目录结构:\n - {results_dir}\n - {latency_results_dir}\n - {original_results_dir}")
    
    # 运行延迟测试
    results = await run_latency_tests()
    
    print("="*50)
    print(" 实验完成! ")
    print(f" 结果保存在 {latency_results_dir} 目录下 ")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
