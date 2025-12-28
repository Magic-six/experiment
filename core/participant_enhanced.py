"""
增强参与方模块 - 集成网络模拟功能的参与方实现
"""

import logging
import asyncio
import random
import zlib
import os
from typing import List, Union, Optional, Tuple, Any, Dict

import sys
import os

# 添加父目录到Python导入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

from communication.async_socket_communication import AsyncSocketCommunication
from utils.config import HOST, DEFAULT_RECV_TIMEOUT, MIN_RECV_TIMEOUT, MAX_RECV_TIMEOUT, MAX_RETRY_COUNT, RETRY_DELAY
from network.network_simulator import NetworkSimulator, NetworkCondition, NETWORK_CONDITIONS

logger = logging.getLogger('lagrange_protocol')

class EnhancedParticipant:
    """
    增强的协议参与方类，具有网络模拟功能
    
    每个参与方都拥有:
      - 通信对象 (AsyncSocketCommunication)
      - 自己的私有 x
      - 公共 x^*
      - q (素数模数)
      - 网络模拟器
    """
    def __init__(
        self, 
        name: str, 
        port: int, 
        x: int, 
        x_star: int, 
        q: int,
        network_condition: Union[str, NetworkCondition] = "local"
    ) -> None:
        """
        初始化参与方
        
        Args:
            name: 参与方名称
            port: 通信端口
            x: 私有坐标
            x_star: 插值点坐标
            q: 素数模数
            network_condition: 网络条件名称或对象
        """
        self.name = name
        self.x = x % q
        self.x_star = x_star % q
        self.q = q
        self.host = HOST

        # 异步通信对象
        self.comm = AsyncSocketCommunication(name, port)
        
        # 检查是否有自定义网络参数
        if isinstance(network_condition, str) and os.environ.get('USE_NETWORK_SIMULATION', '').lower() == 'true':
            # 从环境变量读取自定义参数
            if all(key in os.environ for key in ['CUSTOM_MIN_DELAY', 'CUSTOM_MAX_DELAY', 'CUSTOM_PACKET_LOSS', 'CUSTOM_BANDWIDTH']):
                custom_condition = NetworkCondition(
                    name=f"自定义网络环境",
                    min_delay=float(os.environ['CUSTOM_MIN_DELAY']),
                    max_delay=float(os.environ['CUSTOM_MAX_DELAY']),
                    packet_loss_rate=float(os.environ['CUSTOM_PACKET_LOSS']),
                    bandwidth_limit_kbps=int(os.environ['CUSTOM_BANDWIDTH'])
                )
                self.network_simulator = NetworkSimulator(custom_condition)
                logger.info(f"{self.name} 使用自定义网络条件: {custom_condition}")
            else:
                # 使用预定义条件
                self.network_simulator = NetworkSimulator(network_condition)
                logger.info(f"{self.name} 使用预定义网络条件: {network_condition}")
        else:
            # 直接使用传入的条件
            self.network_simulator = NetworkSimulator(network_condition)
        
        # 通信统计
        self.packet_loss_count = 0
        self.total_packets = 0
        self.total_bytes_sent = 0
        self.total_network_delay = 0.0
        
    @property
    def network_condition(self) -> NetworkCondition:
        """获取当前网络条件"""
        return self.network_simulator.condition
    
    async def start(self) -> None:
        """启动异步通信服务"""
        await self.comm.start()
    
    async def close(self) -> None:
        """关闭异步通信服务"""
        await self.comm.close()
    
    async def send_value(self, other: 'EnhancedParticipant', value_str: Union[str, int, float]) -> bool:
        """
        异步发送字符串给other，经过网络模拟
        确保数据以整数形式发送，避免科学计数法
        
        Args:
            other: 接收消息的参与方
            value_str: 要发送的值
            
        Returns:
            是否成功发送
        """
        # 确保数据以整数形式发送，避免科学计数法
        if isinstance(value_str, (int, float)):
            data_to_send = str(int(value_str))
        else:
            try:
                num = float(value_str)
                if 'e' in value_str.lower() or '.' in value_str:
                    data_to_send = str(int(num))
                else:
                    data_to_send = value_str
            except (ValueError, TypeError):
                data_to_send = value_str
        
        # 模拟网络影响
        self.total_packets += 1
        data_size = len(data_to_send.encode('utf-8'))
        self.total_bytes_sent += data_size
        
        # 添加重试逻辑，提高成功率
        retries = 0
        while retries <= MAX_RETRY_COUNT:
            # 模拟网络效应(延迟、丢包)
            success = await self.network_simulator.simulate_network_effects(data_size)
            if success:
                # 如果网络模拟成功，发送数据
                await self.comm.send_data(
                    target_ip=other.host,
                    target_port=other.comm.port,
                    data=data_to_send
                )
                return True
            else:
                # 模拟丢包时重试
                self.packet_loss_count += 1
                retries += 1
                if retries <= MAX_RETRY_COUNT:
                    logger.warning(f"{self.name} 到 {other.name} 的数据包丢失，重试 {retries}/{MAX_RETRY_COUNT}")
                    await asyncio.sleep(RETRY_DELAY)  # 等待一小段时间再重试
                else:
                    logger.warning(f"{self.name} 发送到 {other.name} 的数据包最终丢失: {data_to_send[:10]}...")
                    return False
        
        return False
        
    async def send_values_batch(self, values_to_send: List[Tuple['EnhancedParticipant', Union[str, int, float]]]) -> Dict['EnhancedParticipant', bool]:
        """
        批量发送多个消息到不同参与方
        
        Args:
            values_to_send: 需要发送的(参与方，值)列表
            
        Returns:
            参与方到发送结果的映射
        """
        # 并行发送所有消息
        send_tasks = [self.send_value(recipient, value) for recipient, value in values_to_send]
        results = await asyncio.gather(*send_tasks)
        
        # 构建结果映射
        return {values_to_send[i][0]: results[i] for i in range(len(values_to_send))}
    
    async def recv_values(self, expected_count: int, wait_sec: float = DEFAULT_RECV_TIMEOUT) -> List[int]:
        """
        异步接收指定数量的值，使用自适应超时
        
        Args:
            expected_count: 期望接收的消息数量
            wait_sec: 基础超时时间（秒）
            
        Returns:
            包含接收到的整数值的列表
        """
        # 在真实环境中，接收端无法模拟网络延迟和丢包，这由发送端模拟
        # 计算智能超时时间
        adjusted_timeout = self.calculate_timeout(wait_sec)
        
        try:
            # 尝试接收数据
            values = await self.comm.recv_values(expected_count, adjusted_timeout)
            return values
        except asyncio.TimeoutError:
            # 如果超时，记录并抛出异常
            logger.warning(f"{self.name} 接收数据超时 (超时时间: {adjusted_timeout}s)")
            raise
    
    def calculate_timeout(self, base_timeout: float) -> float:
        """
        计算自适应超时时间
        
        Args:
            base_timeout: 基础超时时间
            
        Returns:
            调整后的超时时间
        """
        condition = self.network_simulator.condition
        
        if condition.name == "本地网络":
            # 本地网络使用基础超时
            return base_timeout
            
        # 根据网络条件的不同属性来调整超时时间
        # 1. 根据最大延迟调整
        delay_factor = min(condition.max_delay / 1000.0 * 3, 5.0)  # 将毫秒转换为秒
        
        # 2. 根据丢包率调整
        loss_factor = 1.0
        if condition.packet_loss_rate > 0.05:
            loss_factor = 1.5  # 高丢包率需要更长超时
        elif condition.packet_loss_rate > 0.01:
            loss_factor = 1.2  # 中度丢包率
        
        # 3. 根据带宽调整
        bandwidth_factor = 1.0
        if condition.bandwidth_limit_kbps and condition.bandwidth_limit_kbps < 500:
            bandwidth_factor = 1.5  # 低带宽需要更长超时
        
        # 计算最终超时时间，确保在有效范围内
        timeout = base_timeout * delay_factor * loss_factor * bandwidth_factor
        return max(MIN_RECV_TIMEOUT, min(timeout, MAX_RECV_TIMEOUT))
