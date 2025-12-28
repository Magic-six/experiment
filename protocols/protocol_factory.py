"""
协议工厂模块 - 根据环境配置创建适当的参与方
"""

import os
import logging
from typing import Type, Union, Any

import sys
import os

# 添加父目录到Python导入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

from core.participant import Participant
from core.participant_enhanced import EnhancedParticipant

logger = logging.getLogger('lagrange_protocol')

def get_participant_class() -> Type[Union[Participant, EnhancedParticipant]]:
    """
    获取当前应使用的参与方类
    
    根据环境变量决定是否使用具有网络模拟功能的增强参与方类
    
    Returns:
        参与方类
    """
    # 检查环境变量，决定是否使用网络模拟
    use_network_simulation = os.environ.get('USE_NETWORK_SIMULATION', '').lower() == 'true'
    
    if use_network_simulation:
        logger.info("使用增强参与方类(带网络模拟)")
        return EnhancedParticipant
    else:
        logger.info("使用标准参与方类")
        return Participant

def create_participant(*args, **kwargs) -> Union[Participant, EnhancedParticipant]:
    """
    创建参与方实例
    
    Args:
        *args: 传递给参与方构造函数的位置参数
        **kwargs: 传递给参与方构造函数的关键字参数
        
    Returns:
        参与方实例
    """
    # 获取当前应使用的参与方类
    participant_class = get_participant_class()
    
    # 如果使用增强参与方，检查是否需要添加网络类型参数
    if participant_class == EnhancedParticipant and 'network_condition' not in kwargs:
        # 从环境变量获取网络类型
        network_type = os.environ.get('NETWORK_TYPE', 'local')
        kwargs['network_condition'] = network_type
    
    # 创建并返回参与方实例
    return participant_class(*args, **kwargs)
