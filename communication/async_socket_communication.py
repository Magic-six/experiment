"""
异步Socket通信模块 - 实现基于asyncio的网络通信
"""

import asyncio
import logging
import socket
from typing import List, Dict, Optional
import random

# 不在这里配置日志，使用主程序的日志配置

class AsyncSocketCommunication:
    def __init__(self, name: str, port: int = 0, host: str = '127.0.0.1', max_bandwidth: Optional[int] = None):
        """
        异步Socket通信模块初始化
        :param name: 实例名称（用于标识不同通信节点）
        :param port: 本地监听端口，0表示动态分配
        :param host: 本地绑定地址（默认本地环回）
        :param max_bandwidth: 最大发送带宽（字节/秒），None表示无限制
        """
        # 初始化日志记录器
        self.logger = logging.getLogger(f"AsyncSocketCommunication[{name}]")
        
        # 基础配置
        self.name = name
        self.port = port
        self.host = host
        self.max_bandwidth = max_bandwidth
        
        # 接收数据存储
        self.received_data: List[str] = []
        
        # 服务器相关属性
        self.server = None
        self.is_running = False
        self.server_task = None
        
        # 连接池管理
        self.connections: Dict[str, asyncio.StreamWriter] = {}
        self.connection_locks: Dict[str, asyncio.Lock] = {}
        
        # 通信统计
        self.send_data_size = 0
        self.recv_data_size = 0
        self.send_rounds = 0
        self.recv_rounds = 0
        self.stats_lock = asyncio.Lock()
        self.data_lock = asyncio.Lock()
        
        # 添加数据到达事件，避免轮询导致的死锁问题
        self.data_available = asyncio.Event()
    
    async def start(self):
        """启动异步服务器"""
        try:
            self.server = await asyncio.start_server(
                self.handle_client, self.host, self.port
            )
            
            # 获取实际绑定的端口（如果是动态分配）
            addr = self.server.sockets[0].getsockname()
            if self.port == 0:
                self.port = addr[1]
                self.logger.info(f"动态分配端口: {self.port}")
            
            self.is_running = True
            self.logger.info(f"异步服务器监听中 {addr[0]}:{addr[1]}...")
            
            # 启动服务器任务
            self.server_task = asyncio.create_task(self.server.serve_forever())
            
        except Exception as e:
            self.logger.error(f"启动服务器失败: {e}")
            raise
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        处理客户端连接（异步方式）
        """
        addr = writer.get_extra_info('peername')
        self.logger.info(f"接受来自 {addr} 的连接")
        
        try:
            while self.is_running:
                # 异步接收数据
                try:
                    # 添加超时读取，避免永久阻塞
                    data = await asyncio.wait_for(reader.readline(), timeout=30.0)
                    if not data:
                        break
                except asyncio.TimeoutError:
                    # 连接超时检查
                    if writer.is_closing():
                        break
                    continue
                
                # 更新接收统计（仅字节计数，轮次计数移到recv_values）
                async with self.stats_lock:
                    self.recv_data_size += len(data)
                
                # 解码数据并存储
                try:
                    decoded_data = data.decode('utf-8').strip()
                    self.logger.info(f"收到消息: {decoded_data}")
                    async with self.data_lock:
                        self.received_data.append(decoded_data)
                        # 优化：数据添加后立即设置事件，无论之前状态如何
                        # 这确保recv_values方法能够及时获知有新数据到达
                        self.data_available.set()
                except UnicodeDecodeError:
                    self.logger.warning("无法解码数据")
        
        except Exception as e:
            self.logger.error(f"处理客户端错误: {e}")
        finally:
            # 确保连接关闭
            try:
                if not writer.is_closing():
                    writer.close()
                    await writer.wait_closed()
            except Exception:
                pass
            
            self.logger.info(f"连接关闭 {addr}")
            
            # 确保事件被设置，防止任何等待操作永久阻塞
            if not self.data_available.is_set():
                self.data_available.set()
    
    async def get_connection(self, target_ip: str, target_port: int) -> asyncio.StreamWriter:
        """
        获取或创建与目标地址的连接
        使用连接池避免频繁创建和销毁连接
        """
        conn_key = f"{target_ip}:{target_port}"
        
        # 检查连接是否已存在且有效
        if conn_key in self.connections:
            writer = self.connections[conn_key]
            if not writer.is_closing():
                return writer
            else:
                # 清理已关闭的连接
                del self.connections[conn_key]
                if conn_key in self.connection_locks:
                    del self.connection_locks[conn_key]
        
        # 为该连接创建锁，避免并发创建
        if conn_key not in self.connection_locks:
            self.connection_locks[conn_key] = asyncio.Lock()
        
        async with self.connection_locks[conn_key]:
            # 再次检查，防止在获取锁期间已被创建
            if conn_key in self.connections and not self.connections[conn_key].is_closing():
                return self.connections[conn_key]
            
            # 创建新连接
            try:
                reader, writer = await asyncio.open_connection(target_ip, target_port)
                self.connections[conn_key] = writer
                self.logger.info(f"建立连接到 {target_ip}:{target_port}")
                return writer
            except Exception as e:
                self.logger.error(f"连接到 {target_ip}:{target_port} 失败: {e}")
                raise
    
    async def send_data(self, target_ip: str, target_port: int, data: str, retries: int = 3) -> int:
        """
        异步发送数据到目标地址（带重试机制和连接池）
        确保数据以精确整数形式发送，不使用科学计数法
        """
        # 确保数据不会以科学计数法形式发送
        try:
            # 尝试将数据转换为浮点数然后再转换为整数，这样可以避免科学计数法
            # 这适用于发送整数的情况
            if isinstance(data, (int, float)) or (isinstance(data, str) and ('e' in data.lower() or '.' in data)):
                if isinstance(data, str):
                    num_value = float(data)
                else:
                    num_value = data
                # 检查是否为整数
                if num_value.is_integer():
                    data = str(int(num_value))
        except (ValueError, TypeError):
            # 如果转换失败，保留原始数据
            pass
        
        data_bytes = (data + '\n').encode('utf-8')  # 添加换行符作为分隔符
        data_len = len(data_bytes)
        attempt = 0
        
        while attempt <= retries:
            try:
                writer = await self.get_connection(target_ip, target_port)
                
                if self.max_bandwidth:
                    # 带宽限制发送
                    sent = 0
                    chunk_size = min(self.max_bandwidth // 10, data_len)  # 分10块发送
                    
                    while sent < data_len:
                        chunk = data_bytes[sent:sent+chunk_size]
                        writer.write(chunk)
                        await writer.drain()
                        
                        sent += len(chunk)
                        # 控制带宽
                        await asyncio.sleep(len(chunk) / self.max_bandwidth)
                else:
                    # 无带宽限制发送
                    writer.write(data_bytes)
                    await writer.drain()
                
                # 更新发送统计
                async with self.stats_lock:
                    self.send_data_size += data_len
                    self.send_rounds += 1
                
                self.logger.info(f"发送数据到 {target_ip}:{target_port}: {data}")
                return data_len
                
            except Exception as e:
                # 连接失败时清理
                conn_key = f"{target_ip}:{target_port}"
                if conn_key in self.connections:
                    del self.connections[conn_key]
                
                self.logger.warning(f"发送错误: {e}, 尝试 {attempt}/{retries}")
                attempt += 1
                
                # 指数退避重试
                if attempt <= retries:
                    await asyncio.sleep(0.1 * (2 ** attempt) + random.random() * 0.1)
        
        self.logger.error(f"发送失败，已达最大重试次数: {data}")
        return 0
    
    async def recv_values(self, expected_count: int, wait_sec: float = 5.0) -> List[int]:
        """
        异步接收指定数量的值
        使用优化的数据到达事件机制，避免死锁
        直接处理精确整数值，不再需要处理科学计数法
        """
        deadline = asyncio.get_event_loop().time() + wait_sec
        
        while True:
            # 检查是否有足够数据
            async with self.data_lock:
                # 先清除事件，确保下一次数据到达时会正确触发
                # 只有当收到数据时才会重新设置事件
                if self.data_available.is_set():
                    # 如果事件已设置但数据不足，先清除它
                    # 这样后续新数据到达时handle_client会重新设置它
                    self.data_available.clear()
                    
                available = len(self.received_data)
                if available >= expected_count:
                    # 取出需要的数据，假设接收到的都是精确整数
                    res = []
                    for _ in range(expected_count):
                        data_str = self.received_data.pop(0)
                        # 直接转换为整数
                        # 如果数据包含科学计数法或小数，尝试精确转换
                        try:
                            if 'e' in data_str.lower():
                                # 如果仍然收到科学计数法，使用精确转换
                                base, exp = data_str.lower().split('e')
                                if '.' in base:
                                    base_int_part, base_dec_part = base.split('.')
                                    base_dec_part = base_dec_part.rstrip('0')
                                    combined_int = int(base_int_part + base_dec_part)
                                    exp = int(exp) - len(base_dec_part)
                                else:
                                    combined_int = int(base)
                                    exp = int(exp)
                                result = combined_int * (10 ** exp)
                                res.append(result)
                            elif '.' in data_str:
                                # 处理小数，确保精确转换为整数
                                res.append(int(float(data_str)))
                            else:
                                # 直接转换整数
                                res.append(int(data_str))
                        except ValueError:
                            self.logger.error(f"无法转换数据为整数: {data_str}")
                            # 尝试浮点数转换
                            try:
                                res.append(int(float(data_str)))
                            except:
                                # 如果都失败，记录错误并返回0
                                res.append(0)
                    # 记录接收轮次
                    async with self.stats_lock:
                        self.recv_rounds += 1
                    # 如果还有更多数据，重新设置事件通知
                    if self.received_data:
                        self.data_available.set()
                    return res
            
            # 检查是否超时
            current_time = asyncio.get_event_loop().time()
            if current_time > deadline:
                async with self.data_lock:
                    self.logger.warning(f"{self.name} 等待接收超时, 目前已有 {len(self.received_data)} 条.")
                    # 返回已有的所有数据
                    res = []
                    while self.received_data and len(res) < expected_count:
                        data_str = self.received_data.pop(0)
                        # 直接转换为整数
                        try:
                            if 'e' in data_str.lower():
                                # 如果仍然收到科学计数法，使用精确转换
                                base, exp = data_str.lower().split('e')
                                if '.' in base:
                                    base_int_part, base_dec_part = base.split('.')
                                    base_dec_part = base_dec_part.rstrip('0')
                                    combined_int = int(base_int_part + base_dec_part)
                                    exp = int(exp) - len(base_dec_part)
                                else:
                                    combined_int = int(base)
                                    exp = int(exp)
                                result = combined_int * (10 ** exp)
                                res.append(result)
                            elif '.' in data_str:
                                # 处理小数，确保精确转换为整数
                                res.append(int(float(data_str)))
                            else:
                                # 直接转换整数
                                res.append(int(data_str))
                        except ValueError:
                            self.logger.error(f"无法转换数据为整数: {data_str}")
                            # 尝试浮点数转换
                            try:
                                res.append(int(float(data_str)))
                            except:
                                # 如果都失败，记录错误并返回0
                                res.append(0)
                    # 记录接收轮次
                    async with self.stats_lock:
                        self.recv_rounds += 1
                    # 如果还有更多数据，重新设置事件通知
                    if self.received_data:
                        self.data_available.set()
                    return res
            
            # 计算剩余等待时间
            remaining_time = deadline - current_time
            if remaining_time <= 0:
                continue  # 超时，继续循环检查
            
            # 等待数据到达或超时
            self.logger.debug(f"{self.name} 等待数据，剩余时间: {remaining_time:.2f}秒")
            try:
                # 等待数据到达或超时
                await asyncio.wait_for(self.data_available.wait(), timeout=remaining_time)
                # 数据到达后，清除事件以避免虚假唤醒
                self.data_available.clear()
            except asyncio.TimeoutError:
                # 超时，记录并继续循环检查
                self.logger.debug(f"{self.name} 等待超时，继续检查数据")
            except Exception as e:
                # 其他异常，记录并继续尝试
                self.logger.error(f"{self.name} 接收数据时发生异常: {e}")
            # 继续下一轮循环检查
    
    async def close(self):
        """关闭服务器并释放所有连接（优化版本，避免卡住）"""
        # 对于网络环境，建议将超时时间调整为：
        # - 服务器关闭超时 ：至少1-2秒
        # - 服务器任务取消超时 ：至少0.5秒
        # - 连接关闭超时 ：至少0.5秒
        self.logger.info(f"{self.name} 开始关闭连接...")
        self.is_running = False
        
        # 确保事件被设置，唤醒所有等待的recv_values
        self.data_available.set()
        
        # 并行处理服务器关闭和连接关闭，避免顺序等待导致的卡住
        server_close_tasks = []
        
        # 关闭服务器（带超时）
        if self.server:
            self.server.close()
            # 使用更短的超时任务
            server_close_tasks.append(asyncio.create_task(
                asyncio.wait_for(self.server.wait_closed(), timeout=0.05)))
            self.logger.debug(f"{self.name} 服务器开始关闭")
        
        # 等待服务器任务完成（带更短超时）
        if self.server_task:
            self.server_task.cancel()
            server_close_tasks.append(asyncio.create_task(
                asyncio.wait_for(self.server_task, timeout=0.05)))
            self.logger.debug(f"{self.name} 服务器任务开始取消")
        
        # 处理服务器相关任务
        if server_close_tasks:
            try:
                results = await asyncio.gather(*server_close_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.warning(f"{self.name} 服务器关闭任务 {i} 异常: {result}")
                    else:
                        self.logger.debug(f"{self.name} 服务器关闭任务 {i} 完成")
            except Exception as e:
                self.logger.error(f"{self.name} 处理服务器关闭任务时发生错误: {e}")
            self.logger.info(f"{self.name} 服务器关闭完成")
        
        # 并行关闭所有连接，每个连接最多等待0.05秒
        close_tasks = []
        for conn_key, writer in list(self.connections.items()):
            async def close_conn(key, w):
                try:
                    w.close()
                    # 最多等待0.05秒关闭连接
                    await asyncio.wait_for(w.wait_closed(), timeout=0.05)
                    self.logger.debug(f"{self.name} 关闭连接到 {key}")
                    return True
                except Exception as e:
                    self.logger.warning(f"{self.name} 关闭连接 {key} 超时或错误: {e}")
                    return False
            
            close_tasks.append(close_conn(conn_key, writer))
        
        # 等待所有连接关闭任务完成
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # 清空连接池和数据
        self.connections.clear()
        self.connection_locks.clear()
        self.received_data.clear()
        
        self.logger.info(f"{self.name} 所有连接关闭完成")
    
    def get_communication_stats(self) -> Dict[str, int]:
        """
        获取通信统计信息
        """
        return {
            'send_data_size': self.send_data_size,
            'recv_data_size': self.recv_data_size,
            'send_rounds': self.send_rounds,
            'recv_rounds': self.recv_rounds
        }


class PortManager:
    """
    端口管理器，负责动态分配和释放端口
    """
    def __init__(self, min_port: int = 6100, max_port: int = 6200):
        self.min_port = min_port
        self.max_port = max_port
        self.available_ports = set(range(min_port, max_port + 1))
        self.port_lock = asyncio.Lock()
        self.logger = logging.getLogger("PortManager")
    
    async def get_port(self) -> int:
        """获取一个可用端口"""
        async with self.port_lock:
            if not self.available_ports:
                raise RuntimeError("没有可用的端口，请检查端口配置")
            
            # 随机选择一个端口，避免连续使用同一端口
            port = random.choice(list(self.available_ports))
            self.available_ports.remove(port)
            self.logger.info(f"分配端口: {port}")
            return port
    
    async def release_port(self, port: int):
        """释放端口"""
        async with self.port_lock:
            if self.min_port <= port <= self.max_port:
                self.available_ports.add(port)
                self.logger.info(f"释放端口: {port}")
            else:
                self.logger.warning(f"尝试释放无效端口: {port}")
    
    def get_available_count(self) -> int:
        """获取可用端口数量"""
        return len(self.available_ports)


# 全局端口管理器实例
port_manager = PortManager()
