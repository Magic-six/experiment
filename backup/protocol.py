"""
协议模块 - 实现三方和四方安全拉格朗日插值协议
"""

import logging
import asyncio
import time
import os
from typing import List, Tuple, Dict, Optional, Union, Any

from multiplicative_group import PrimeOrderCyclicGroup
from communication.async_socket_communication import PortManager
from participant import Participant
from utils import mini_one_share, mini_zero_share
from config import DEFAULT_RECV_TIMEOUT
from protocol_factory import create_participant

# 创建端口管理器实例
port_manager = PortManager(min_port=6100, max_port=6200)

# 初始化logger
logger = logging.getLogger('lagrange_protocol')

async def three_party_compute(
    x_i: int, 
    x_j: int, 
    x_k: int, 
    x_star: int, 
    group: PrimeOrderCyclicGroup, 
    party_i_id: Optional[int] = None, 
    party_j_id: Optional[int] = None, 
    party_k_id: Optional[int] = None
) -> Optional[Tuple[int, int, int, int, int, float]]:
    """
    三方安全计算拉格朗日基函数值
    
    Args:
        x_i, x_j, x_k: 三个参与方的x值
        x_star: 插值点
        group: 循环群
        party_i_id, party_j_id, party_k_id: 参与方的实际标号
        
    Returns:
        (结果, 发送数据大小, 接收数据大小, 发送轮数, 接收轮数, 运行时间) 的元组，失败时返回None
    """
    # 转换为整型
    x_i = int(x_i)
    x_j = int(x_j)
    x_k = int(x_k)
    
    # 记录开始时间
    overall_start_time = time.time()
    
    # 使用实际标号或默认标号
    p_i_name = f"P_{party_i_id}" if party_i_id is not None else "P_i"
    p_j_name = f"P_{party_j_id}" if party_j_id is not None else "P_j"
    p_k_name = f"P_{party_k_id}" if party_k_id is not None else "P_k"
    
    logger.info(f"开始three_party_compute: {p_i_name}(x={x_i}), {p_j_name}(x={x_j}), {p_k_name}(x={x_k}), x_star={x_star}")

    # 初始化三个参与方，使用动态端口分配
    try:
        port_i = await port_manager.get_port()
        port_j = await port_manager.get_port()
        port_k = await port_manager.get_port()
        
        P_i = create_participant(p_i_name, port_i, x_i, x_star, group.p)
        P_j = create_participant(p_j_name, port_j, x_j, x_star, group.p)
        P_k = create_participant(p_k_name, port_k, x_k, x_star, group.p)
        
        # 并行启动所有参与方的通信服务
        await asyncio.gather(
            P_i.start(),
            P_j.start(),
            P_k.start()
        )
    except Exception as e:
        logger.error(f"初始化参与方失败: {e}")
        # 释放端口
        if 'port_i' in locals(): await port_manager.release_port(port_i)
        if 'port_j' in locals(): await port_manager.release_port(port_j)
        if 'port_k' in locals(): await port_manager.release_port(port_k)
        return None

    #---------------------------------------------
    # 第1部分: 计算 (x_i - x_j)(x_i - x_k)
    #  1) 三次1分享 => r_{11..}, r_{21..}, r_{31..}
    #---------------------------------------------
    # 这里我们一次性生成三行, each row=[r1, r2, r3], 乘积=1
    try:
        share_mat = [mini_one_share(group) for _ in range(3)]
        r11,r12,r13 = share_mat[0]
        r21,r22,r23 = share_mat[1]
        r31,r32,r33 = share_mat[2]

        # 2) 交叉发送
        #   P_i发送: r21*x_i -> P_j, r31*x_i -> P_k
        masked_ij = (r21 * P_i.x) % group.p
        masked_ik = (r31 * P_i.x) % group.p
        
        #   P_j发送: r12*x_j -> P_i, r32*x_j -> P_k
        masked_ji = (r12 * P_j.x) % group.p
        masked_jk = (r32 * P_j.x) % group.p
        
        #   P_k发送: r13*x_k -> P_i, r23*x_k -> P_j
        masked_ki = (r13 * P_k.x) % group.p
        masked_kj = (r23 * P_k.x) % group.p
        
        # 优化通信顺序，避免死锁
        logger.info("开始第一轮数据交换...")
        
        # 先启动所有接收任务
        recv_i_task = asyncio.create_task(P_i.recv_values(2, wait_sec=DEFAULT_RECV_TIMEOUT))
        recv_j_task = asyncio.create_task(P_j.recv_values(2, wait_sec=DEFAULT_RECV_TIMEOUT))
        recv_k_task = asyncio.create_task(P_k.recv_values(2, wait_sec=DEFAULT_RECV_TIMEOUT))
        
        # 然后并行发送所有消息
        logger.info("开始发送第一轮数据...")
        await asyncio.gather(
            P_i.send_value(P_j, str(int(masked_ij))),
            P_i.send_value(P_k, str(int(masked_ik))),
            P_j.send_value(P_i, str(int(masked_ji))),
            P_j.send_value(P_k, str(int(masked_jk))),
            P_k.send_value(P_i, str(int(masked_ki))),
            P_k.send_value(P_j, str(int(masked_kj)))
        )
        logger.info("第一轮数据发送完成")
        
        # 等待所有接收完成
        logger.info("等待所有参与方接收第一轮数据...")
        vals_i = await recv_i_task
        vals_j = await recv_j_task
        vals_k = await recv_k_task
        logger.info("所有参与方接收第一轮数据完成")
        
        # 检查接收结果
        for party, vals, party_name in [(P_i, vals_i, p_i_name), 
                                       (P_j, vals_j, p_j_name), 
                                       (P_k, vals_k, p_k_name)]:
            if len(vals) < 2:
                logger.error(f"{party_name} 未收到足够掩码, 协议中断. 仅收到 {len(vals)} 个值")
                await cleanup_resources([P_i, P_j, P_k], [port_i, port_j, port_k])
                return None
            logger.info(f"{party_name} 成功接收第一轮数据: {vals}")

        # 3) 组合: x_i^2 + x_j*x_k
        #   x_j*x_k = (r12*x_j)*(r13*x_k)
        chunk_j = vals_i[0]
        chunk_k = vals_i[1]
        x_i_sqr = (P_i.x * P_i.x) % group.p
        x_j_x_k = (r11 * chunk_j * chunk_k) % group.p  # r12*r13=1? => yes, r11*r12*r13=1
        A = (x_i_sqr + x_j_x_k) % group.p

        # 4) 0分享 => [a1,a2,a3], P_j->P_i:(a2 - x_i*x_k), P_k->P_i:(a3 - x_i*x_j)
        zero_sh = mini_zero_share(group)
        a1, a2, a3 = zero_sh

        #   P_j 算 x_i*x_k
        chunkj_i = vals_j[0]
        chunkj_k = vals_j[1]
        xixk = (chunkj_i * r22 * chunkj_k) % group.p
        delta_j = (a2 - xixk) % group.p

        # P_k 算 x_i*x_j
        chunkk_i = vals_k[0]
        chunkk_j = vals_k[1]
        xixj = (chunkk_i * chunkk_j * r33) % group.p
        delta_k = (a3 - xixj) % group.p

        # 优化delta数据发送和接收
        # 先启动接收任务
        recv_delta_task = asyncio.create_task(P_i.recv_values(2, wait_sec=DEFAULT_RECV_TIMEOUT))
        
        # 然后并行发送delta数据
        await asyncio.gather(
            P_j.send_value(P_i, str(delta_j)),
            P_k.send_value(P_i, str(delta_k))
        )
        
        # 等待接收完成
        vals2_i = await recv_delta_task
        if len(vals2_i) < 2:
            logger.error(f"[{p_i_name}] 未收到足够 0分享数据, 中断. 仅收到 {len(vals2_i)} 个值")
            await cleanup_resources([P_i, P_j, P_k], [port_i, port_j, port_k])
            return None
        logger.info(f"{p_i_name} 成功接收delta数据: {vals2_i}")
        
        d_j = vals2_i[0]
        d_k = vals2_i[1]
        denominator = (a1 + A + d_j + d_k) % group.p

        #---------------------------------------------
        # 第2部分: 计算 (x^*-x_j)(x^*-x_k) => 再1次1分享 => [r1,r2,r3]
        #---------------------------------------------
        share_last = mini_one_share(group)
        r1, r2, r3 = share_last

        # P_j => P_i: r2*(x^*-x_j)
        masked_j = (r2*((P_j.x_star - P_j.x)%group.p))%group.p
        
        # P_k => P_i: r3*(x^*-x_k)
        masked_k_ = (r3*((P_k.x_star - P_k.x)%group.p))%group.p
        
        # 优化最后一轮数据交换
        # 先启动接收任务
        recv_final_task = asyncio.create_task(P_i.recv_values(2, wait_sec=DEFAULT_RECV_TIMEOUT))
        
        # 然后并行发送数据
        await asyncio.gather(
            P_j.send_value(P_i, str(int(masked_j))),
            P_k.send_value(P_i, str(int(masked_k_)))
        )
        
        # 等待接收完成
        vals3_i = await recv_final_task
        if len(vals3_i) < 2:
            logger.error(f"[{p_i_name}] 未收到足够 (x^*-x_j)(x^*-x_k) 数据, 中断. 仅收到 {len(vals3_i)} 个值")
            await cleanup_resources([P_i, P_j, P_k], [port_i, port_j, port_k])
            return None
        logger.info(f"{p_i_name} 成功接收(x^*-x_j)(x^*-x_k)数据: {vals3_i}")
        
        vj_ = vals3_i[0]
        vk_ = vals3_i[1]
        numerator = (r1 * vj_ * vk_) % group.p

        # 最终除法
        denom_inv = group.mod_inverse(denominator)
        final_res = (numerator * denom_inv) % group.p

    except Exception as e:
        logger.error(f"三方计算过程出错: {e}")
        await cleanup_resources([P_i, P_j, P_k], [port_i, port_j, port_k])
        return None
        
    # 关闭通信并释放资源
    try:
        # 并行关闭所有通信连接和释放端口
        await cleanup_resources([P_i, P_j, P_k], [port_i, port_j, port_k])
    except Exception as e:
        logger.error(f"资源清理过程出错: {e}")
        # 忽略资源释放错误，不影响结果返回
        pass

    # 计算通信统计信息
    send_data_size = P_i.comm.send_data_size + P_j.comm.send_data_size + P_k.comm.send_data_size
    recv_data_size = P_i.comm.recv_data_size + P_j.comm.recv_data_size + P_k.comm.recv_data_size
    send_rounds = P_i.comm.send_rounds + P_j.comm.send_rounds + P_k.comm.send_rounds
    recv_rounds = P_i.comm.recv_rounds + P_j.comm.recv_rounds + P_k.comm.recv_rounds
    
    # 如果使用了网络模拟，将数据写入环境变量供测试脚本使用
    if hasattr(P_i, 'network_condition'):
        os.environ['TOTAL_SEND_BYTES'] = str(send_data_size)
        os.environ['TOTAL_RECV_BYTES'] = str(recv_data_size)
    
    # 记录结束时间并返回结果
    overall_end_time = time.time()
    run_time = overall_end_time - overall_start_time
    
    return final_res, send_data_size, recv_data_size, send_rounds, recv_rounds, run_time

async def cleanup_resources(participants: List, ports: List[int]) -> None:
    """
    清理资源（关闭连接、释放端口）
    
    Args:
        participants: 参与方列表
        ports: 端口列表
    """
    # 创建关闭参与方的任务
    close_tasks = [p.close() for p in participants]
    
    # 创建释放端口的任务
    release_tasks = [port_manager.release_port(port) for port in ports]
    
    # 并行执行所有任务
    await asyncio.gather(*close_tasks, *release_tasks, return_exceptions=True)
