"""
协议扩展模块 - 实现四方安全计算协议和拉格朗日插值函数
"""

import logging
import asyncio
import time
import os
from typing import List, Tuple, Dict, Optional, Union, Any

from multiplicative_group import PrimeOrderCyclicGroup
from communication.async_socket_communication import PortManager
from participant import Participant
from utils import mini_one_share, mini_zero_share, generate_triples
from config import (
    DEFAULT_RECV_TIMEOUT, DEFAULT_PRIME, DEFAULT_GENERATOR,
    MIN_PARTIES, MAX_PARTIES
)
from protocol import port_manager, cleanup_resources
from protocol_factory import create_participant

# 初始化logger
logger = logging.getLogger('lagrange_protocol')

async def four_party_compute(
    x_i: int, 
    x_j: int, 
    x_k: int, 
    x_l: int,
    x_star: int, 
    group: PrimeOrderCyclicGroup, 
    party_i_id: Optional[int] = None, 
    party_j_id: Optional[int] = None, 
    party_k_id: Optional[int] = None,
    party_l_id: Optional[int] = None
) -> Optional[Tuple[int, int, int, int, int, float]]:
    """
    四方安全计算拉格朗日基函数值
    
    Args:
        x_i, x_j, x_k, x_l: 四个参与方的x值
        x_star: 插值点
        group: 循环群
        party_i_id, party_j_id, party_k_id, party_l_id: 参与方的实际标号
        
    Returns:
        (结果, 发送数据大小, 接收数据大小, 发送轮数, 接收轮数, 运行时间) 的元组，失败时返回None
    """
    # 转换为整型
    x_i = int(x_i)
    x_j = int(x_j)
    x_k = int(x_k)
    x_l = int(x_l)
    
    # 记录开始时间
    overall_start_time = time.time()
    
    # 使用实际标号或默认标号
    p_i_name = f"P_{party_i_id}" if party_i_id is not None else "P_i"
    p_j_name = f"P_{party_j_id}" if party_j_id is not None else "P_j"
    p_k_name = f"P_{party_k_id}" if party_k_id is not None else "P_k"
    p_l_name = f"P_{party_l_id}" if party_l_id is not None else "P_l"
    
    logger.info(f"开始four_party_compute: {p_i_name}(x={x_i}), {p_j_name}(x={x_j}), {p_k_name}(x={x_k}), {p_l_name}(x={x_l}), x_star={x_star}")
    
    # 初始化四个参与方，使用动态端口分配
    try:
        port_i = await port_manager.get_port()
        port_j = await port_manager.get_port()
        port_k = await port_manager.get_port()
        port_l = await port_manager.get_port()
        
        P_i = create_participant(p_i_name, port_i, x_i, x_star, group.p)
        P_j = create_participant(p_j_name, port_j, x_j, x_star, group.p)
        P_k = create_participant(p_k_name, port_k, x_k, x_star, group.p)
        P_l = create_participant(p_l_name, port_l, x_l, x_star, group.p)
        
        # 并行启动所有参与方的通信服务
        await asyncio.gather(
            P_i.start(),
            P_j.start(),
            P_k.start(),
            P_l.start()
        )
    except Exception as e:
        logger.error(f"初始化参与方失败: {e}")
        # 释放端口
        for port_var in ['port_i', 'port_j', 'port_k', 'port_l']:
            if port_var in locals():
                await port_manager.release_port(locals()[port_var])
        return None

    try:
        #---------------------------------------------
        # 第1部分: 计算 (x_i-x_j)(x_i-x_k)(x_i-x_l)
        #  1) 四次1分享 => r_{11..}, r_{21..}, r_{31..}, r_{41..};一次0分享 => r_{1..}
        #---------------------------------------------
        # 这里我们一次性生成四行, each row=[r1, r2, r3, r4], 乘积=1
        share_mat = [mini_one_share(group, 4) for _ in range(4)]
        share_mat_0 = mini_zero_share(group, 4)
        r11,r12,r13,r14 = share_mat[0]
        r21,r22,r23,r24 = share_mat[1]
        r31,r32,r33,r34 = share_mat[2]
        r41,r42,r43,r44 = share_mat[3]
        r1,r2,r3,r4 = share_mat_0

        # 2) 交叉发送
        #   P_i发送: r21*x_i -> P_j, r31*x_i -> P_k, r41*x_i -> P_l
        masked_ij = (r21 * P_i.x) % group.p
        masked_ik = (r31 * P_i.x) % group.p
        masked_il = (r41 * P_i.x) % group.p
        
        #   P_j发送: r12*x_j -> P_i, r32*x_j -> P_k, r42*x_j -> P_l; r2*x_j -> P_i
        masked_ji = (r12 * P_j.x) % group.p
        masked_jk = (r32 * P_j.x) % group.p
        masked_jl = (r42 * P_j.x) % group.p
        
        #   P_k发送: r13*x_k -> P_i, r23*x_k -> P_j, r43*x_k -> P_l; r3*x_k -> P_i
        masked_ki = (r13 * P_k.x) % group.p
        masked_kj = (r23 * P_k.x) % group.p
        masked_kl = (r43 * P_k.x) % group.p
        
        #   P_l发送: r14*x_l -> P_i, r24*x_l -> P_j, r34*x_l -> P_k; r4*x_l -> P_i
        masked_li = (r14 * P_l.x) % group.p
        masked_lj = (r24 * P_l.x) % group.p
        masked_lk = (r34 * P_l.x) % group.p
        
        # 并行发送所有消息
        await asyncio.gather(
            P_i.send_value(P_j, str(int(masked_ij))),
            P_i.send_value(P_k, str(int(masked_ik))),
            P_i.send_value(P_l, str(int(masked_il))),
            P_j.send_value(P_i, str(int(masked_ji))),
            P_j.send_value(P_k, str(int(masked_jk))),
            P_j.send_value(P_l, str(int(masked_jl))),
            P_k.send_value(P_i, str(int(masked_ki))),
            P_k.send_value(P_j, str(int(masked_kj))),
            P_k.send_value(P_l, str(int(masked_kl))),
            P_l.send_value(P_i, str(int(masked_li))),
            P_l.send_value(P_j, str(int(masked_lj))),
            P_l.send_value(P_k, str(int(masked_lk)))
        )

        # P_i 等待 3 个值
        vals_i = await P_i.recv_values(3, wait_sec=DEFAULT_RECV_TIMEOUT)
        if len(vals_i) < 3:
            logger.error(f"[{p_i_name}] 未收到足够掩码, 协议中断.")
            await cleanup_resources([P_i, P_j, P_k, P_l], [port_i, port_j, port_k, port_l])
            return None

        # 3) 组合
        chunki_j = vals_i[0]
        chunki_k = vals_i[1]
        chunki_l = vals_i[2]
        x_i_sqr = (P_i.x * P_i.x) % group.p
        x_i_cub = (P_i.x * P_i.x * P_i.x) % group.p
        x_j_x_k_1 = (r11 * chunki_j * chunki_k * chunki_l) % group.p

        masked_j = (r2 + P_j.x) % group.p
        masked_k = (r3 + P_k.x) % group.p
        masked_l = (r4 + P_l.x) % group.p
        
        # 并行发送
        await asyncio.gather(
            P_j.send_value(P_i, str(int(masked_j))),
            P_k.send_value(P_i, str(int(masked_k))),
            P_l.send_value(P_i, str(int(masked_l)))
        )

        # P_i 等待 3 个值
        vals_i_1 = await P_i.recv_values(3, wait_sec=DEFAULT_RECV_TIMEOUT)
        if len(vals_i_1) < 3:
            logger.error(f"[{p_i_name}] 未收到足够掩码, 协议中断.")
            await cleanup_resources([P_i, P_j, P_k, P_l], [port_i, port_j, port_k, port_l])
            return None
            
        chunkj = vals_i_1[0]
        chunkk = vals_i_1[1]
        chunkl = vals_i_1[2]
        x_j_x_k_2 = (x_i_sqr * ((r1 + chunkj + chunkk + chunkl) % group.p)) % group.p
        A = (x_i_cub - x_j_x_k_1 - x_j_x_k_2) % group.p

        # 4) 0分享 => [a1,a2,a3,a4]
        zero_sh = mini_zero_share(group, 4)
        a1, a2, a3, a4 = zero_sh
        
        # 其他参与方接收
        vals_j = await P_j.recv_values(3, wait_sec=DEFAULT_RECV_TIMEOUT)
        vals_k = await P_k.recv_values(3, wait_sec=DEFAULT_RECV_TIMEOUT)
        vals_l = await P_l.recv_values(3, wait_sec=DEFAULT_RECV_TIMEOUT)
        
        # 检查接收数据
        for party, vals, party_name in [(P_j, vals_j, p_j_name), 
                                       (P_k, vals_k, p_k_name), 
                                       (P_l, vals_l, p_l_name)]:
            if len(vals) < 3:
                logger.error(f"{party_name} 未收到足够掩码, 协议中断.")
                await cleanup_resources([P_i, P_j, P_k, P_l], [port_i, port_j, port_k, port_l])
                return None
        
        # P_j 计算
        chunkj_i = vals_j[0]
        chunkj_k = vals_j[1]
        chunkj_l = vals_j[2]
        xixkxl = (chunkj_i * r22 * chunkj_k * chunkj_l) % group.p
        delta_j = (a2 + xixkxl) % group.p

        # P_k 计算
        chunkk_i = vals_k[0]
        chunkk_j = vals_k[1]
        chunkk_l = vals_k[2]
        xixjxl = (chunkk_i * chunkk_j * r33 * chunkk_l) % group.p
        delta_k = (a3 + xixjxl) % group.p

        # P_l 计算
        chunkl_i = vals_l[0]
        chunkl_j = vals_l[1]
        chunkl_k = vals_l[2]
        xixjxk = (chunkl_i * chunkl_j * chunkl_k * r44) % group.p
        delta_l = (a4 + xixjxk) % group.p

        # 并行发送delta数据
        await asyncio.gather(
            P_j.send_value(P_i, str(int(delta_j))),
            P_k.send_value(P_i, str(int(delta_k))),
            P_l.send_value(P_i, str(int(delta_l)))
        )
        
        # P_i 等待 3个值
        vals2_i = await P_i.recv_values(3, wait_sec=DEFAULT_RECV_TIMEOUT)
        if len(vals2_i) < 3:
            logger.error(f"[{p_i_name}] 未收到足够 0分享数据, 中断.")
            await cleanup_resources([P_i, P_j, P_k, P_l], [port_i, port_j, port_k, port_l])
            return None
            
        d_j = vals2_i[0]
        d_k = vals2_i[1]
        d_l = vals2_i[2]
        denominator = (a1 + A + d_j + d_k + d_l) % group.p

        #---------------------------------------------
        # 第2部分: 计算 (x^*-x_j)(x^*-x_k)(x^*-x_l) => 再1次1分享
        #---------------------------------------------
        share_last = mini_one_share(group, 4)
        rr1, rr2, rr3, rr4 = share_last

        # P_j => P_i: rr2*(x^*-x_j)
        masked_j_1 = (rr2*((P_j.x_star - P_j.x)%group.p))%group.p
        
        # P_k => P_i: rr3*(x^*-x_k)
        masked_k_1 = (rr3*((P_k.x_star - P_k.x)%group.p))%group.p
        
        # P_l => P_i: rr4*(x^*-x_l)
        masked_l_1 = (rr4*((P_l.x_star - P_l.x)%group.p))%group.p
        
        # 并行发送
        await asyncio.gather(
            P_j.send_value(P_i, str(int(masked_j_1))),
            P_k.send_value(P_i, str(int(masked_k_1))),
            P_l.send_value(P_i, str(int(masked_l_1)))
        )

        # P_i 接收3个
        vals3_i = await P_i.recv_values(3, wait_sec=DEFAULT_RECV_TIMEOUT)
        if len(vals3_i) < 3:
            logger.error(f"[{p_i_name}] 未收到足够 (x^*-x_j)(x^*-x_k)(x^*-x_l) 数据, 中断.")
            await cleanup_resources([P_i, P_j, P_k, P_l], [port_i, port_j, port_k, port_l])
            return None
            
        vj_ = vals3_i[0]
        vk_ = vals3_i[1]
        vl_ = vals3_i[2]
        numerator = (rr1 * vj_ * vk_ * vl_) % group.p

        # 最终除法
        denom_inv = group.mod_inverse(denominator)
        final_res = (numerator * denom_inv) % group.p

    except Exception as e:
        logger.error(f"四方计算过程出错: {e}")
        await cleanup_resources([P_i, P_j, P_k, P_l], [port_i, port_j, port_k, port_l])
        return None
    
    # 关闭通信并释放资源
    try:
        await cleanup_resources([P_i, P_j, P_k, P_l], [port_i, port_j, port_k, port_l])
    except Exception:
        # 忽略资源释放错误
        pass

    # 记录结束时间
    overall_end_time = time.time()
    run_time = overall_end_time - overall_start_time

    # 四方总的通信量
    send_data_size = P_i.comm.send_data_size + P_j.comm.send_data_size + P_k.comm.send_data_size + P_l.comm.send_data_size
    recv_data_size = P_i.comm.recv_data_size + P_j.comm.recv_data_size + P_k.comm.recv_data_size + P_l.comm.recv_data_size
    # 四方总通信轮次
    send_rounds = P_i.comm.send_rounds + P_j.comm.send_rounds + P_k.comm.send_rounds + P_l.comm.send_rounds
    recv_rounds = P_i.comm.recv_rounds + P_j.comm.recv_rounds + P_k.comm.recv_rounds + P_l.comm.recv_rounds
    
    # 如果使用了网络模拟，将数据写入环境变量供测试脚本使用
    if hasattr(P_i, 'network_condition'):
        os.environ['TOTAL_SEND_BYTES'] = str(send_data_size)
        os.environ['TOTAL_RECV_BYTES'] = str(recv_data_size)

    return final_res, send_data_size, recv_data_size, send_rounds, recv_rounds, run_time

async def secure_lagrange_interpolation(
    points: List[Tuple[int, int]], 
    x_star: int,
    p: int = DEFAULT_PRIME,
    g: int = DEFAULT_GENERATOR
) -> int:
    """
    安全拉格朗日插值函数，支持多方安全计算
    
    Args:
        points: 数据点列表，每个元素为(x, y)元组
        x_star: 要插值的x坐标
        p: 素数模数
        g: 生成元
    
    Returns:
        y_star: x_star处的插值结果
    """
    # 记录整个协议的开始时间
    overall_start_time = time.time()

    # 总的数据通信量
    overall_send_data_size = 0
    overall_recv_data_size = 0

    # 通信轮次
    overall_round = 2
    overall_send_round = 0
    overall_recv_round = 0

    # 获取参与方数量
    party_num = len(points)
    
    # 确保参与方数量在有效范围内
    if not (MIN_PARTIES <= party_num <= MAX_PARTIES):
        logger.error(f"参与方数量 {party_num} 超出有效范围({MIN_PARTIES}-{MAX_PARTIES})")
        raise ValueError(f"参与方数量 {party_num} 超出有效范围({MIN_PARTIES}-{MAX_PARTIES})")
    
    logger.info(f"参与方数量: {party_num}")

    # 从points中提取x和y坐标
    x = [None]  # 索引从1开始
    y = [None]  # 索引从1开始
    for i, (xi, yi) in enumerate(points, 1):
        x.append(xi)
        y.append(yi)

    # 初始化循环群
    logger.info("初始化循环群...")
    group = PrimeOrderCyclicGroup(p, g)
    logger.info("循环群初始化完成")

    # 划分三元组或四元组
    logger.info("生成三元组...")
    result = generate_triples(party_num)
    logger.info(f"生成的三元组: {result}")

    # 计算所有拉格朗日基函数
    temp = [0 for i in range(1, party_num+1)]
    final_value = [1 for i in range(1, party_num+1)]
    run_time_temp = [0 for i in range(1, party_num+1)]
    logger.info("开始计算拉格朗日基函数...")
    
    try:
        from protocol import three_party_compute  # 避免循环引用
        
        # 对每个参与方创建一个用于存储任务和结果的结构
        computation_tasks = []
        task_mapping = {}  # 映射任务到参与方和三/四元组
        
        # 将三元组/四元组计算函数异步并行调用
        logger.info("并行计算拉格朗日基函数...")
        
        if party_num % 2 == 1:  # 奇数情况，全是三元组
            logger.info("使用three_party_compute并行计算")
            for i in range(1, party_num+1):
                for triple in result:
                    if triple[0] == i:
                        logger.info(f"创建三元组并行任务 {triple}")
                        # 创建并行计算任务
                        task = three_party_compute(
                            x[triple[0]], x[triple[1]], x[triple[2]], x_star, group,
                            party_i_id=triple[0], party_j_id=triple[1], party_k_id=triple[2]
                        )
                        computation_tasks.append(task)
                        # 记录任务到参与方和三元组的映射
                        task_mapping[len(computation_tasks) - 1] = (i, triple)
        else:  # 偶数情况，有三元组和四元组
            logger.info("使用three_party_compute和four_party_compute并行计算")
            for i in range(1, party_num+1):
                for triple in result:
                    if (triple[0] == i) and (len(triple) == 3):  # 三元组
                        logger.info(f"创建三元组并行任务 {triple}")
                        task = three_party_compute(
                            x[triple[0]], x[triple[1]], x[triple[2]], x_star, group,
                            party_i_id=triple[0], party_j_id=triple[1], party_k_id=triple[2]
                        )
                        computation_tasks.append(task)
                        task_mapping[len(computation_tasks) - 1] = (i, triple)
                    elif (triple[0] == i) and (len(triple) == 4):  # 四元组
                        logger.info(f"创建四元组并行任务 {triple}")
                        task = four_party_compute(
                            x[triple[0]], x[triple[1]], x[triple[2]], x[triple[3]], x_star, group,
                            party_i_id=triple[0], party_j_id=triple[1], party_k_id=triple[2], party_l_id=triple[3]
                        )
                        computation_tasks.append(task)
                        task_mapping[len(computation_tasks) - 1] = (i, triple)
        
        # 使用asyncio.gather并行执行所有计算任务
        logger.info(f"开始执行 {len(computation_tasks)} 个并行计算任务")
        task_results = await asyncio.gather(*computation_tasks, return_exceptions=True)
        logger.info("并行计算完成，收集结果")
        
        # 处理计算结果
        success_count = 0
        for i, result_data in enumerate(task_results):
            if isinstance(result_data, Exception):
                # 记录失败
                party_i, triple = task_mapping[i]
                logger.error(f"任务 {i} 失败: 参与方 {party_i}, 元组 {triple}, 错误: {result_data}")
                continue
                
            if result_data:  # 非None结果表示成功
                success_count += 1
                party_i, _ = task_mapping[i]
                temp_val, send_data_temp, recv_data_temp, send_rounds_temp, recv_rounds_temp, run_time_val = result_data
                temp[party_i-1] = temp_val
                overall_send_data_size += send_data_temp
                overall_recv_data_size += recv_data_temp
                overall_send_round += send_rounds_temp
                overall_recv_round += recv_rounds_temp
                final_value[party_i-1] = (final_value[party_i-1] * temp_val) % group.p
                run_time_temp[party_i-1] = max(run_time_temp[party_i-1], run_time_val)
        
        logger.info(f"成功完成 {success_count}/{len(computation_tasks)} 个计算任务")
        
        # 应用最终乘法
        for i in range(1, party_num+1):
            final_value[i-1] = (final_value[i-1] * y[i]) % group.p

        # 计算最终的插值点值
        y_star = 0
        for i in range(1, party_num+1):
            y_star = (y_star + final_value[i-1]) % group.p

        # 计算每个计算函数的最大运行时间
        max_compute_time = max(run_time_temp) if run_time_temp else 0
        
        # 计算整个协议的运行时间
        overall_end_time = time.time()
        run_time = overall_end_time - overall_start_time

        logger.info("\n=== 插值结果 ===")
        logger.info(f"参与方数量：{party_num}")
        logger.info(f"在x={x_star}处的插值点y={y_star}(mod {p})")

        logger.info("\n=== 通信统计 ===")
        logger.info(f"协议运行时间: {run_time:.2f} 秒 (包含初始化、计算和清理)")
        logger.info(f"最长计算时间: {max_compute_time:.2f} 秒")
        logger.info(f"协议通信量：send={overall_send_data_size} 字节, recv={overall_recv_data_size} 字节")
        logger.info(f"协议通信轮次: Overall_Round = {overall_round}, all_send_rounds = {overall_send_round}，all_recv_rounds = {overall_recv_round}\n")

        # 如果使用了网络模拟，将总结果写入环境变量
        if 'USE_NETWORK_SIMULATION' in os.environ and os.environ['USE_NETWORK_SIMULATION'].lower() == 'true':
            os.environ['TOTAL_SEND_BYTES'] = str(overall_send_data_size)
            os.environ['TOTAL_RECV_BYTES'] = str(overall_recv_data_size)
            os.environ['TOTAL_RUN_TIME'] = str(run_time)
            os.environ['MAX_COMPUTE_TIME'] = str(max_compute_time)

        return y_star
        
    except Exception as e:
        logger.error(f"安全拉格朗日插值计算失败: {type(e).__name__}: {e}")
        # 如果安全计算失败，回退到普通计算
        logger.warning("回退到普通计算...")
        # 实现简单的拉格朗日插值作为备用
        y_star = 0
        for i in range(1, party_num+1):
            xi, yi = x[i], y[i]
            # 计算拉格朗日基多项式
            l_i = 1
            for j in range(1, party_num+1):
                if i != j:
                    xj = x[j]
                    # 使用模运算进行除法（乘以模逆元）
                    numerator = (x_star - xj) % p
                    denominator = (xi - xj) % p
                    try:
                        inv_denominator = group.mod_inverse(denominator)
                        l_i = (l_i * numerator * inv_denominator) % p
                    except Exception as e:
                        logger.error(f"计算拉格朗日基时出错: {e}")
                        raise
            # 累加结果
            y_star = (y_star + yi * l_i) % p
        logger.info(f"普通计算结果: y={y_star}(mod {p})")
        return y_star
