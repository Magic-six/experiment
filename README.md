# 多方安全拉格朗日插值协议

## 项目概述

本项目实现了一种**专用的多方安全拉格朗日插值协议**，允许多个参与方在不泄露各自私有输入的前提下，共同计算拉格朗日插值结果。与通用MPC框架（如MP-SPDZ）相比，本协议针对拉格朗日插值的代数结构进行了专门优化，实现了**更低的通信量**和**更少的通信轮次**。

### 核心特性

- **乘法秘密分享**：使用份额乘积为1的秘密分享方案，避免了在线除法通信
- **低通信复杂度**：通信量 O(n) 域元素，通信轮次 O(1)
- **TLS加密支持**：可选的传输层安全加密
- **通信统计**：详细的发送/接收字节数和轮次统计
- **网络模拟**：支持模拟不同网络条件（LAN/WAN）

### 主要功能

1. **安全拉格朗日插值**：三方/四方安全计算协议
2. **通信量分析**：精确统计通信开销，支持与MP-SPDZ对比
3. **网络环境模拟**：可模拟不同网络条件下的协议性能
4. **TLS安全通信**：支持TLS加密的安全通道
5. **性能分析与可视化**：详细的运行数据统计和可视化图表

## 项目结构

```
experiment/
├── core/                    # 核心模块
│   ├── multiplicative_group.py   # 素数阶乘法循环群
│   └── participant.py            # 协议参与方
│
├── communication/           # 通信模块
│   ├── async_socket_communication.py  # 异步Socket通信（支持TLS）
│   └── generate_certs.py         # TLS证书生成工具
│
├── network/                 # 网络相关
│   └── network_simulator.py      # 网络环境模拟器
│
├── protocols/               # 协议实现
│   ├── protocol.py              # 三方/四方安全计算协议
│   ├── protocol_extension.py     # 完整拉格朗日插值协议
│   └── protocol_factory.py       # 参与方工厂
│
├── utils/                   # 工具类
│   ├── config.py                # 配置参数
│   └── utils.py                 # 秘密分享等工具函数
│
├── logs/                    # 日志目录
├── network_test_results/    # 实验结果目录
├── benchmarks/              # 基准测试代码
│   └── LagrangeInterpolation.mpc  # MP-SPDZ对比代码
├── main.py                  # 基础版本入口
├── main_optimized.py        # 优化版本入口（推荐）
├── latency_experiment.py    # 网络延迟实验
└── .gitignore               # Git忽略配置
```

## 快速开始

### 运行优化版本（推荐）

```bash
# 运行3方安全拉格朗日插值
python main_optimized.py 3

# 运行5方安全拉格朗日插值
python main_optimized.py 5

# 运行测试模式（验证正确性）
python main_optimized.py 3 test
```

### 运行网络延迟实验

```bash
python latency_experiment.py
```

## 版本说明

### 1. 优化版本 (main_optimized.py) - 推荐

针对性能和通信量优化的版本，提供详细的通信统计。

**特点：**
- 详细的通信量统计（发送/接收字节数、轮次）
- 支持TLS加密通信
- 优化的异步并发处理
- 支持可配置的参与方数量（3-28方）

### 2. 基础版本 (main.py)

基础版本专注于协议本身的功能验证。

### 3. 网络模拟版本 (latency_experiment.py)

模拟不同网络条件（LAN/WAN），研究协议在真实网络环境中的性能表现。

**预设网络环境：**
- 局域网 (10ms/50ms延迟)
- 广域网 (50ms/100ms/200ms延迟)

## 依赖库

- Python 3.8+
- asyncio: 异步通信
- matplotlib: 图表绘制
- numpy: 数据处理
- sympy: 数学计算
- ssl: TLS加密（标准库）

## 安装指南

1. 克隆项目代码：
```bash
git clone https://github.com/Magic-six/experiment.git
cd experiment
```

2. 安装依赖库：
```bash
pip install matplotlib numpy sympy
```

3. （可选）生成TLS证书：
```bash
python communication/generate_certs.py
```

## 实验结果

实验结果将保存在以下位置：
- 原始数据: `network_test_results/latency_experiment/latency_comparison_results.json`
- 性能对比图表: `network_test_results/latency_experiment/*.png`
- 运行日志: `logs/latency_experiment.log` 或 `logs/lagrange_protocol.log`

## 与 MP-SPDZ 对比

项目提供了 MP-SPDZ 基准测试代码 `benchmarks/LagrangeInterpolation.mpc`，用于通信量对比实验。

### 使用方法

1. 将文件复制到 MP-SPDZ 目录：
```bash
cp benchmarks/LagrangeInterpolation.mpc /path/to/MP-SPDZ/Programs/Source/
```

2. 编译并运行：
```bash
cd /path/to/MP-SPDZ
./compile.py LagrangeInterpolation
./Scripts/semi.sh LagrangeInterpolation    # Semi协议
./Scripts/hemi.sh LagrangeInterpolation    # Hemi协议
./Scripts/shamir.sh LagrangeInterpolation  # Shamir协议
```

### 通信量对比结果（示例）

| 参与方数 | 本协议 | MP-SPDZ (Semi) | MP-SPDZ (Shamir) |
|---------|-------|----------------|------------------|
| 3 | ~KB | 0.21 MB | 0.08 MB |
| 13 | ~KB | 33.3 MB | 53.5 MB |
| 28 | ~KB | 363.3 MB | 1249.7 MB |

## 技术特点

1. **专用协议优化**：针对拉格朗日插值的代数结构专门设计
2. **乘法秘密分享**：使用份额乘积为1的分享方案，除法转化为本地求逆
3. **低通信复杂度**：相比通用MPC框架减少1-2个数量级的通信量
4. **异步通信**：基于Python asyncio实现高效并发通信
5. **TLS安全**：支持传输层加密保护通信安全
6. **详细统计**：精确统计通信字节数和轮次

## 协议原理

### 拉格朗日插值公式

$$y^* = \sum_{i=1}^{n} y_i \cdot L_i(x^*), \quad L_i(x^*) = \prod_{j \neq i} \frac{x^* - x_j}{x_i - x_j}$$

### 安全计算流程

1. **乘法秘密分享**：生成随机数 $(r_1, r_2, r_3)$ 满足 $r_1 \cdot r_2 \cdot r_3 = 1$
2. **掩盖交换**：各方发送 $r_i \cdot x_i$ 给其他方，隐藏真实输入
3. **本地计算**：接收方利用份额关系计算乘积，无需额外通信
4. **除法本地化**：分母计算后本地求逆，避免安全除法的高通信开销
5. **结果聚合**：各基函数值加权求和得到最终插值结果

### 通信复杂度对比

| 协议 | 通信量 | 通信轮次 |
|-----|-------|---------|
| 本协议 | O(n) 域元素 | O(1) |
| MP-SPDZ (Beaver) | O(n² × k) 域元素 | O(n² × log k) |

其中 n 为参与方数量，k 为定点数精度。

## 注意事项

- 日志文件保存在 `logs` 目录下
- 修改 `utils/config.py` 可以调整协议参数（素数、生成元等）
- TLS证书文件不会被提交到Git仓库

## 许可证

MIT License
