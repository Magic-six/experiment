"""
工具模块 - 包含辅助函数和通用功能
"""

import logging
import random
from typing import List, Tuple, Union, Optional

# 配置logging
def setup_logging(filename: str = 'lagrange_protocol.log', console_output: bool = True) -> None:
    """
    配置日志系统
    
    Args:
        filename: 日志文件名
        console_output: 是否输出到控制台
    """
    # 基本配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s',
        filename=filename,
        filemode='w',
        encoding='utf-8'
    )
    
    # 如果需要控制台输出
    if console_output:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
    
    return logging.getLogger('lagrange_protocol')

def generate_triples(n: int) -> List[Tuple[int, ...]]:
    """
    将n个数划分为若干个三元组或四元组
    
    Args:
        n: 参与方数量
        
    Returns:
        包含三元组和四元组的列表
    """
    triples = []
    
    if n % 2 == 1:  # 奇数情况，全部是三元组
        for i in range(1, n + 1):
            remaining = [num for num in range(1, n + 1) if num != i]
            pairs = []
            # 每两个一组，确保没有重叠
            for j in range(0, len(remaining), 2):
                pair = tuple(remaining[j:j + 2])
                pairs.append(pair)
            # 添加i到每个pair中，形成三元组
            for pair in pairs:
                triple = (i,) + pair
                triples.append(triple)
    else:  # 偶数情况，有一个四元组
        for i in range(1, n + 1):
            remaining = [num for num in range(1, n + 1) if num != i]
            pairs = []
            # 每两个一组，确保没有重叠
            for j in range(0, len(remaining) - 1, 2):
                pair = tuple(remaining[j:j + 2])
                pairs.append(pair)
            # 添加i到每个pair中，形成三元组
            for pair in pairs:
                triple = (i,) + pair
                triples.append(triple)
            # 处理剩余的元素
            if len(remaining) % 2 == 1:
                remaining_element = remaining[-1]
                triples[-1] = triples[-1] + (remaining_element,)
    
    return triples

def mini_one_share(group, size: int = 3) -> List[int]:
    """
    一次性生成乘积为1的随机数列表
    
    Args:
        group: 循环群对象
        size: 要生成的随机数数量，默认为3
        
    Returns:
        长度为size的列表，乘积为1 mod p
    """
    if size < 2:
        raise ValueError("Size must be at least 2")
    
    # 生成size-1个随机数
    shares = [random.randint(1, group.p-1) for _ in range(size-1)]
    
    # 计算它们的乘积
    product = 1
    for share in shares:
        product = (product * share) % group.p
    
    # 计算最后一个数，使得所有数的乘积为1
    last_share = group.mod_inverse(product)
    shares.append(last_share)
    
    return shares

def mini_zero_share(group, size: int = 3) -> List[int]:
    """
    一次性生成和为0的随机数列表
    
    Args:
        group: 循环群对象
        size: 要生成的随机数数量，默认为3
        
    Returns:
        长度为size的列表，和为0 mod p
    """
    if size < 2:
        raise ValueError("Size must be at least 2")
    
    # 生成size-1个随机数
    shares = [random.randint(0, group.p-1) for _ in range(size-1)]
    
    # 计算它们的和
    total = sum(shares) % group.p
    
    # 计算最后一个数，使得所有数的和为0
    last_share = (-total) % group.p
    shares.append(last_share)
    
    return shares
