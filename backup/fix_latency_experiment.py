"""
修复延迟实验问题：
1. 分离图表结果到独立文件夹
2. 修复中文显示问题
"""

import os
import shutil
import matplotlib
import matplotlib.pyplot as plt
import platform
from pathlib import Path

# 创建新的文件夹结构
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "network_test_results")
OLD_RESULTS_DIR = os.path.join(RESULTS_DIR, "original_experiment")
NEW_RESULTS_DIR = os.path.join(RESULTS_DIR, "latency_experiment")

def setup_font():
    """设置matplotlib字体以正确显示中文"""
    print("正在配置中文字体...")
    
    if platform.system() == 'Windows':
        # 尝试使用多种Windows中文字体
        chinese_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'FangSong']
        font_found = False
        
        for font_name in chinese_fonts:
            try:
                test_font = matplotlib.font_manager.FontProperties(fname=f"C:/Windows/Fonts/{font_name}.ttf")
                if test_font:
                    print(f"找到中文字体: {font_name}")
                    plt.rcParams['font.sans-serif'] = [font_name]
                    plt.rcParams['axes.unicode_minus'] = False
                    font_found = True
                    break
            except:
                continue
                
        if not font_found:
            print("警告: 未找到中文字体，将使用默认字体")
    
    elif platform.system() == 'Darwin':  # macOS
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
    
    else:  # Linux
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
        plt.rcParams['axes.unicode_minus'] = False
        
    print("字体配置完成")

def organize_files():
    """将实验结果文件分类整理到不同文件夹"""
    print("正在整理实验文件...")
    
    # 确保目标文件夹存在
    os.makedirs(OLD_RESULTS_DIR, exist_ok=True)
    os.makedirs(NEW_RESULTS_DIR, exist_ok=True)
    
    # 移动原始实验文件
    original_files = [
        'communication_comparison.png',
        'network_runtime_detail.png',
        'network_test_results.json',
        'network_test_results_optimized.json',
        'runtime_comparison.png',
        'runtime_heatmap.png',
        'success_rate_comparison.png'
    ]
    
    # 移动延迟实验文件
    latency_files = [
        'latency_comparison_results.json',
        'latency_compute_vs_network_time.png',
        'latency_lan_vs_wan_comparison.png',
        'latency_runtime_by_parties.png',
        'latency_runtime_vs_datasize.png'
    ]
    
    # 移动文件到相应文件夹
    for file_name in os.listdir(RESULTS_DIR):
        file_path = os.path.join(RESULTS_DIR, file_name)
        
        # 跳过目录
        if os.path.isdir(file_path):
            if file_name not in ['original_experiment', 'latency_experiment']:
                print(f"跳过目录: {file_name}")
            continue
        
        if file_name in original_files:
            dest = os.path.join(OLD_RESULTS_DIR, file_name)
            try:
                shutil.copy2(file_path, dest)
                print(f"复制文件 {file_name} 到原始实验文件夹")
            except:
                print(f"无法复制文件 {file_name}")
        
        elif file_name in latency_files or file_name.startswith('latency_'):
            dest = os.path.join(NEW_RESULTS_DIR, file_name)
            try:
                shutil.copy2(file_path, dest)
                print(f"复制文件 {file_name} 到延迟实验文件夹")
            except:
                print(f"无法复制文件 {file_name}")
    
    print("文件整理完成")

def update_latency_script():
    """更新延迟比较脚本中的字体配置和输出目录"""
    script_path = os.path.join(BASE_DIR, "latency_comparison.py")
    
    if not os.path.exists(script_path):
        print(f"错误: 无法找到延迟比较脚本: {script_path}")
        return
    
    with open(script_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 更新字体配置
    if "configure_matplotlib_fonts" in content:
        # 替换字体配置函数
        updated_content = content.replace(
            "def configure_matplotlib_fonts():",
            """def configure_matplotlib_fonts():
    \"\"\"配置matplotlib以支持中文字体\"\"\"
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
            print("警告: 未找到中文字体，将使用默认字体")""")
        
        # 更新RESULTS_DIR路径
        updated_content = updated_content.replace(
            "RESULTS_DIR = \"network_test_results\"",
            "RESULTS_DIR = \"network_test_results/latency_experiment\""
        )
        
        # 写回文件
        with open(script_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)
        
        print("已更新延迟比较脚本的字体配置和输出目录")
    else:
        print("警告: 无法在脚本中找到字体配置函数")

if __name__ == "__main__":
    # 设置正确的字体
    setup_font()
    
    # 整理文件
    organize_files()
    
    # 更新延迟脚本
    update_latency_script()
    
    print("\n修复完成! 请重新运行延迟比较实验以生成正确显示中文的图表")
