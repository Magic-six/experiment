"""
参与方模块 - 定义协议参与方类
"""

import logging
import asyncio
from typing import List, Union, Optional, Tuple

from communication.async_socket_communication import AsyncSocketCommunication
from config import HOST

logger = logging.getLogger('lagrange_protocol')

class Participant:
    """
    协议参与方类
    
    每个参与方都拥有:
      - 通信对象 (AsyncSocketCommunication)
      - 自己的私有 x
      - 公共 x^*
      - q (素数模数)
    """
    def __init__(self, name: str, port: int, x: int, x_star: int, q: int) -> None:
        """
        初始化参与方
        
        Args:
            name: 参与方名称
            port: 通信端口
            x: 私有坐标
            x_star: 插值点坐标
            q: 素数模数
        """
        self.name = name
        self.x = x % q
        self.x_star = x_star % q
        self.q = q
        self.host = HOST

        # 异步通信对象
        self.comm = AsyncSocketCommunication(name, port)
    
    async def start(self) -> None:
        """启动异步通信服务"""
        await self.comm.start()
    
    async def close(self) -> None:
        """关闭异步通信服务"""
        await self.comm.close()
    
    async def send_value(self, other: 'Participant', value_str: Union[str, int, float]) -> None:
        """
        异步发送字符串给other
        确保数据以整数形式发送，避免科学计数法
        
        Args:
            other: 接收消息的参与方
            value_str: 要发送的值
        """
        # 确保数据以整数形式发送，避免科学计数法
        if isinstance(value_str, (int, float)):
            # 转换为整数并确保以字符串形式发送
            data_to_send = str(int(value_str))
        else:
            # 检查字符串是否可能是科学计数法表示
            try:
                # 尝试将字符串解析为浮点数，然后转换为整数
                num = float(value_str)
                if 'e' in value_str.lower() or '.' in value_str:
                    # 如果是科学计数法或包含小数点，转换为整数
                    data_to_send = str(int(num))
                else:
                    # 否则保持原字符串
                    data_to_send = value_str
            except (ValueError, TypeError):
                # 如果不是数字，保持原字符串
                data_to_send = value_str
        
        await self.comm.send_data(
            target_ip=other.host,
            target_port=other.comm.port,
            data=data_to_send
        )
    
    async def recv_values(self, expected_count: int, wait_sec: float = 2.0) -> List[int]:
        """
        异步接收指定数量的值
        
        Args:
            expected_count: 期望接收的消息数量
            wait_sec: 超时时间（秒）
            
        Returns:
            包含接收到的整数值的列表
        """
        return await self.comm.recv_values(expected_count, wait_sec)
