# 多方安全拉格朗日插值实验

## 项目概述

本项目实现了基于多方安全计算的拉格朗日插值协议，并提供了各种实验环境和分析工具。主要功能包括：

1. **安全拉格朗日插值**：实现了基于多方安全计算的拉格朗日插值协议
2. **网络环境模拟**：可模拟不同网络条件下的协议运行情况
3. **性能分析**：提供了详细的性能统计和可视化工具
4. **延迟对比实验**：在模拟LAN和WAN环境下（设置具体延迟，如50ms/100ms）进行对比实验

## 简化版项目结构

为了便于维护和使用，项目已经简化为以下结构：

```
experiment/
├─ core/                    # 核心模块
│   ├─ multiplicative_group.py   # 乘法循环群实现
│   └─ participant.py            # 基本参与方实现
│
├─ communication/           # 通信模块
│   └─ async_socket_communication.py  # 异步Socket通信
│
├─ network/                 # 网络相关
│   └─ network_simulator.py      # 网络环境模拟器
│
├─ protocols/               # 协议实现
│   ├─ protocol.py              # 基础协议
│   ├─ protocol_extension.py     # 协议扩展(拉格朗日插值)
│   └─ protocol_factory.py       # 参与方工厂
│
├─ utils/                   # 工具类
│   ├─ config.py                # 配置参数
│   └─ utils.py                 # 实用函数
│
├─ docs/                    # 文档
├─ latency_experiment.py     # 精简版实验入口脚本 
└─ README.md                # 项目文档 
```

## 导入结构与代码组织

本项目使用了基于系统路径的导入方式，确保模块间可以正确导入不会出现循环依赖问题。在每个模块的开头使用以下代码添加父目录到Python导入路径：

```python
import sys
import os

# 添加父目录到Python导入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 
```

这样各模块可以使用以下格式进行导入：

```python
from core.multiplicative_group import PrimeOrderCyclicGroup
from utils.config import DEFAULT_PRIME
from protocols.protocol_extension import secure_lagrange_interpolation
```

## 主要实验

### 1. 延迟对比实验

在模拟的LAN和WAN环境下（设置具体的延迟，如50ms/100ms）进行对比实验，验证协议在高延迟环境下的性能表现，并证明作者强调的“通信量优势”在广域网环境下如何转化为总运行时间的优势。

**运行方式**：
```bash
python latency_experiment.py
```

**实验配置**：
- **网络环境**：
  - 局域网 (10ms延迟)
  - 局域网 (50ms延迟)
  - 广域网 (50ms延迟)
  - 广域网 (100ms延迟)
  - 广域网 (200ms延迟)
- **参与方数量**：3, 5, 7, 9
- **每个配置重复3次**以确保结果可靠

**结果分析**：
- 在广域网环境下，通信量的减少对总运行时间有更显著的影响
- 当参与方数量增加时，通信优势更为明显
- 计算时间vs通信时间的占比分析展示了协议的瓶颈

## 依赖库

- Python 3.7+
- asyncio: 异步通信
- matplotlib: 图表绘制
- numpy: 数据处理
- sympy: 数学计算

## 代码简化说明

项目代码进行了简化优化，主要包括以下几个方面：

### 1. 删除了冗余文件

- 移除了实验固定版本的副本(`run_fixed_comparison.py`、`run_with_pythonpath.sh`等)
- 移除了`experiments`目录下的多余文件，将必要功能集成到单一入口脚本
- 删除了不必要的文档和多余的`README_*.md`文件

### 2. 整合了入口脚本

- 将`run_latency_experiment.py`和`experiments/latency_experiment.py`合并为单一入口脚本`latency_experiment.py`
- 优化了脚本内部结构，删除不必要的代码注释和重复逻辑

### 3. 简化了绘图功能

- 保留了最关键的两个图表：运行时间对比和LAN vs WAN比较图
- 删除了不必要的复杂图表和重复可视化内容

## 项目重构和问题修复

项目经过重构，主要解决了以下问题：

### 导入路径问题

原始版本中存在的问题：
1. **混合导入方式**：代码中混合使用了相对导入和绝对导入
2. **循环导入**：模块之间存在循环导入依赖
3. **包结构不清晰**：重构之前代码的包结构与导入方式不匹配

### 解决方案

1. **使用系统路径导入**：在每个模块中添加父目录到Python导入路径
2. **统一导入方式**：将所有文件的导入方式修改为一致的格式
3. **清晰的目录结构**：将代码按功能分类到不同目录中

### 延迟对比实验优化

1. **分离实验结果**：将不同实验的结果保存到独立的子目录中
2. **优化中文显示**：改进了matplotlib字体配置，确保中文显示正确
3. **增强实验数据分析**：添加更多数据分析和图表生成

## 注意事项

- 实验结果保存在 `network_test_results/latency_experiment` 目录下
- 原始实验结果保存在 `network_test_results/original_experiment` 目录下
- 日志文件保存在 `logs` 目录下
- 修改 `utils/config.py` 可以调整协议参数
