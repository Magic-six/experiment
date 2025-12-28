# 多方安全拉格朗日插值实验

## 项目概述

本项目实现了基于多方安全计算的拉格朗日插值协议，并提供了各种实验环境和分析工具。该协议允许多个参与方在不泄露各自私有输入的前提下，共同计算拉格朗日插值结果。项目包含两个主要版本：基础版本和网络模拟版本。

### 主要功能

1. **安全拉格朗日插值**：实现了基于多方安全计算的拉格朗日插值协议
2. **网络环境模拟**：可模拟不同网络条件下（LAN/WAN）的协议运行情况
3. **延迟对比实验**：在不同网络延迟环境下进行性能对比测试
4. **性能分析与可视化**：提供详细的运行数据统计和可视化图表

## 项目结构

```
experiment/
├── core/                    # 核心模块
│   ├── multiplicative_group.py   # 乘法循环群实现
│   └── participant.py            # 基本参与方实现
│
├── communication/           # 通信模块
│   └── async_socket_communication.py  # 异步Socket通信
│
├── network/                 # 网络相关
│   └── network_simulator.py      # 网络环境模拟器
│
├── protocols/               # 协议实现
│   ├── protocol.py              # 基础协议
│   ├── protocol_extension.py     # 协议扩展(拉格朗日插值)
│   └── protocol_factory.py       # 参与方工厂
│
├── utils/                   # 工具类
│   ├── config.py                # 配置参数
│   └── utils.py                 # 实用函数
│
├── docs/                    # 文档
├── logs/                    # 日志目录
├── main.py                  # 基础版本入口脚本
├── latency_experiment.py    # 网络延迟实验入口脚本
└── config.json              # 配置文件
```

## 两个版本说明

### 1. 基础版本 (main.py)

基础版本专注于协议本身的功能，不模拟网络状态，适合快速测试和理解协议的基本运行过程。

**特点：**
- 直接使用基本的异步通信，无网络延迟模拟
- 专注于协议的正确性验证
- 支持可配置的参与方数量
- 提供测试模式验证插值计算的准确性

**运行方式：**
```bash
python main.py [参与方数量]  # 正常运行
python main.py [参与方数量] test  # 运行测试模式
```

### 2. 网络模拟版本 (latency_experiment.py)

网络模拟版本通过模拟不同网络条件（如局域网和广域网环境下的不同延迟），研究协议在真实网络环境中的性能表现。

**特点：**
- 模拟多种网络环境(局域网/广域网)
- 自定义延迟、丢包率和带宽参数
- 收集并分析性能数据
- 生成可视化性能对比图表

**预设网络环境：**
- 局域网 (10ms延迟)
- 局域网 (50ms延迟)
- 广域网 (50ms延迟)
- 广域网 (100ms延迟)
- 广域网 (200ms延迟)

**运行方式：**
```bash
python latency_experiment.py
```

## 依赖库

- Python 3.7+
- asyncio: 异步通信
- matplotlib: 图表绘制
- numpy: 数据处理
- sympy: 数学计算

## 安装指南

1. 克隆项目代码：
```bash
git clone [仓库URL]
cd lagrange/experiment
```

2. 安装依赖库：
```bash
pip install -r requirements.txt  # 如果有requirements.txt文件
# 或手动安装
pip install matplotlib numpy sympy
```

## 使用示例

### 基础版本示例

```bash
# 运行3方安全计算
python main.py 3

# 运行5方安全计算
python main.py 5

# 运行测试模式
python main.py 3 test
```

### 网络延迟实验示例

```bash
# 运行默认配置的网络延迟对比实验
python latency_experiment.py

# 查看结果
# 结果保存在 network_test_results/latency_experiment 目录下
```

## 实验结果

实验结果将保存在以下位置：
- 原始数据: `network_test_results/latency_experiment/latency_comparison_results.json`
- 性能对比图表: `network_test_results/latency_experiment/*.png`
- 运行日志: `logs/latency_experiment.log` 或 `logs/lagrange_protocol.log`

## 项目技术特点

1. **模块化设计**：代码组织清晰，便于维护和扩展
2. **异步通信**：基于Python asyncio实现高效并发通信
3. **灵活配置**：可通过命令行参数和配置文件调整参数
4. **健壮性**：完善的错误处理和日志记录机制
5. **性能分析**：详细的性能统计和可视化分析工具

## 实现原理

该项目基于多方安全计算原理，使用拉格朗日插值法进行秘密共享和重构，主要过程包括：

1. 初始化：创建循环群和参与方实例
2. 秘密共享：参与方将自己的数据点拆分为多份分享给其他参与方
3. 安全计算：参与方基于接收到的秘密份额进行本地计算
4. 结果聚合：各方计算结果安全聚合得到最终插值结果
5. 通信优化：使用异步通信减少等待时间，提高整体效率

## 注意事项

- 日志文件保存在 `logs` 目录下
- 修改 `utils/config.py` 可以调整协议参数
- 调整 `config.json` 可以修改默认配置
