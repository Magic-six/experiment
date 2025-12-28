"""
网络环境模拟模块 - 用于模拟不同网络环境下的通信条件
"""

import asyncio
import random
import zlib
import time
from typing import Optional, Dict, Any, Union, Tuple, List, Callable

class NetworkCondition:
    """网络环境条件配置类"""
    
    def __init__(
        self,
        name: str,
        min_delay: float = 0.0,
        max_delay: float = 0.0,
        packet_loss_rate: float = 0.0,
        bandwidth_limit_kbps: Optional[int] = None
    ):
        """
        初始化网络环境配置
        
        Args:
            name: 环境名称
            min_delay: 最小延迟(秒)
            max_delay: 最大延迟(秒)
            packet_loss_rate: 丢包率 (0.0-1.0)
            bandwidth_limit_kbps: 带宽限制(kbps)，None表示不限制
        """
        self.name = name
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.packet_loss_rate = min(1.0, max(0.0, packet_loss_rate))
        self.bandwidth_limit_kbps = bandwidth_limit_kbps
    
    def __str__(self) -> str:
        """返回网络环境的可读字符串表示"""
        bw_str = f"{self.bandwidth_limit_kbps} kbps" if self.bandwidth_limit_kbps else "无限制"
        return (f"{self.name}: 延迟={self.min_delay*1000:.0f}-{self.max_delay*1000:.0f}ms, "
                f"丢包率={self.packet_loss_rate*100:.1f}%, 带宽={bw_str}")


# 预定义网络环境
NETWORK_CONDITIONS = {
    "local": NetworkCondition(
        name="本地网络", 
        min_delay=0.001, 
        max_delay=0.005, 
        packet_loss_rate=0.0
    ),
    "lan": NetworkCondition(
        name="局域网", 
        min_delay=0.005, 
        max_delay=0.020, 
        packet_loss_rate=0.001,
        bandwidth_limit_kbps=100000  # 100 Mbps
    ),
    "wan": NetworkCondition(
        name="广域网", 
        min_delay=0.050, 
        max_delay=0.200, 
        packet_loss_rate=0.01,
        bandwidth_limit_kbps=10000  # 10 Mbps
    ),
    "poor_wan": NetworkCondition(
        name="低质量广域网", 
        min_delay=0.100, 
        max_delay=0.500, 
        packet_loss_rate=0.05,
        bandwidth_limit_kbps=1000  # 1 Mbps
    ),
    "satellite": NetworkCondition(
        name="卫星网络", 
        min_delay=0.500, 
        max_delay=1.000, 
        packet_loss_rate=0.03,
        bandwidth_limit_kbps=512  # 512 kbps
    ),
    "iot": NetworkCondition(
        name="IoT网络", 
        min_delay=0.200, 
        max_delay=0.800, 
        packet_loss_rate=0.08,
        bandwidth_limit_kbps=100  # 100 kbps
    ),
    "mobile_4g": NetworkCondition(
        name="4G移动网络", 
        min_delay=0.050, 
        max_delay=0.150, 
        packet_loss_rate=0.02,
        bandwidth_limit_kbps=5000  # 5 Mbps
    ),
    "mobile_5g": NetworkCondition(
        name="5G移动网络", 
        min_delay=0.010, 
        max_delay=0.050, 
        packet_loss_rate=0.005,
        bandwidth_limit_kbps=50000  # 50 Mbps
    )
}


class NetworkSimulator:
    """网络环境模拟器，用于模拟不同网络条件下的通信延迟和丢包、带宽限制"""
    
    def __init__(self, condition: Union[str, NetworkCondition] = "local", use_compression: bool = False):
        """
        初始化网络模拟器
        
        Args:
            condition: 网络条件名称或NetworkCondition对象
            use_compression: 是否启用数据压缩模拟
        """
        if isinstance(condition, str):
            if condition in NETWORK_CONDITIONS:
                self.condition = NETWORK_CONDITIONS[condition]
            else:
                raise ValueError(f"未知的网络条件: {condition}")
        else:
            self.condition = condition
        
        # 数据压缩选项
        self.use_compression = use_compression
        
        # 缓存系统
        self.cache = {}
        self.last_send_time = 0
        self.traffic_queue = []  # 限流队列
        
        # 限制缓存大小
        self.max_cache_size = 100
        
        # 性能统计
        self.compressed_bytes = 0
        self.original_bytes = 0
        self.bandwidth_delays = []  # 带宽延迟记录
    
    def compress_data(self, data_size: int) -> int:
        """
        模拟数据压缩，返回压缩后的大小
        
        Args:
            data_size: 原始数据大小
        
        Returns:
            压缩后的数据大小
        """
        if not self.use_compression:
            return data_size
            
        # 实际应用中，压缩率因数据内容而异，这里使用一个简化的模拟
        # 对于数字数据，假设压缩率在40-70%之间
        compression_ratio = random.uniform(0.4, 0.7)
        compressed_size = int(data_size * compression_ratio)
        
        # 更新统计信息
        self.original_bytes += data_size
        self.compressed_bytes += compressed_size
        
        return max(1, compressed_size)  # 确保数据大小至少为1字节
    
    async def simulate_network_effects(
        self, 
        data_size_bytes: int,
        max_retries: int = 1,
        optimize_for: str = "balanced"
    ) -> bool:
        """
        模拟网络效应(延迟、丢包、带宽限制)
        
        Args:
            data_size_bytes: 数据包大小(字节)
            max_retries: 最大重试次数
            optimize_for: 优化策略 ("speed", "reliability", "balanced")
            
        Returns:
            是否成功传输(True)或丢包(False)
        """
        # 如果启用了压缩，计算压缩后的数据大小
        effective_data_size = self.compress_data(data_size_bytes) if self.use_compression else data_size_bytes
        
        # 检查缓存
        data_hash = hash(f"{effective_data_size}_{time.time_ns() % 10000}")  # 简单模拟数据标识
        if data_hash in self.cache:
            # 缓存命中，只需模拟小延迟
            await asyncio.sleep(self.condition.min_delay * 0.1)  # 缓存命中时的延迟大幅减少
            return True
        
        # 缓存管理
        if len(self.cache) > self.max_cache_size:
            # LRU缓存清理策略
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        # 优化策略
        packet_loss_threshold = self.condition.packet_loss_rate
        if optimize_for == "speed":
            # 速度优先，减少延迟
            delay_factor = 0.8
            packet_loss_threshold *= 1.2  # 增加一点丢包率换取更快速度
        elif optimize_for == "reliability":
            # 可靠性优先，减少丢包
            delay_factor = 1.2
            packet_loss_threshold *= 0.8  # 减少丢包率
        else:  # balanced
            delay_factor = 1.0
        
        # 模拟带宽和设备最大并发连接限制
        current_time = time.time()
        if self.condition.bandwidth_limit_kbps:
            # 限流控制
            if self.traffic_queue and (current_time - self.last_send_time) < 0.05:  # 50ms 内
                # 如果有队列中的流量且时间间隔很短，模拟带宽畅通率下降
                if random.random() < 0.3:  # 30% 几率模拟转发瓶颈
                    return False
        
        # 模拟丢包
        for attempt in range(max_retries + 1):
            if random.random() >= packet_loss_threshold:
                # 计算随机延迟
                base_delay = random.uniform(
                    self.condition.min_delay, 
                    self.condition.max_delay
                ) * delay_factor
                
                # 计算带宽引起的延迟
                bandwidth_delay = 0
                if self.condition.bandwidth_limit_kbps:
                    # 核心带宽计算公式
                    bandwidth_delay = (effective_data_size * 8) / (self.condition.bandwidth_limit_kbps * 1000)
                    
                    # 添加带宽波动
                    jitter = random.uniform(-0.1, 0.2) * bandwidth_delay
                    bandwidth_delay += jitter
                    
                    # 更新最后发送时间
                    self.last_send_time = current_time
                    
                    # 记录带宽延迟
                    self.bandwidth_delays.append(bandwidth_delay)
                    if len(self.bandwidth_delays) > 100:
                        self.bandwidth_delays.pop(0)  # 保持最近100次记录
                
                # 总延迟
                total_delay = base_delay + bandwidth_delay
                
                # 模拟延迟
                await asyncio.sleep(total_delay)
                
                # 更新缓存
                self.cache[data_hash] = current_time
                
                return True
            elif attempt < max_retries:
                # 请求失败但还可以重试
                await asyncio.sleep(0.05)  # 重试前等待短暂停
            else:
                # 超过最大重试次数
                return False
        
        return False  # 默认失败
