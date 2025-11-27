# 视觉驱动的小车抓取机器人 / Vision-Driven Block Picking Robot

完整的视觉驱动自主抓取与投放系统，用于树莓派 5 + Arduino Mega 2560 + USB 摄像头。

## 系统架构 / System Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Raspberry Pi 5 (Python)                                │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │   vision.py  │  │   main.py   │  │car_controller│  │
│  │  (USB Cam)   │─▶│(State Machine)│─▶│  (Serial)   │  │
│  └──────────────┘  └─────────────┘  └──────┬───────┘  │
└─────────────────────────────────────────────┼──────────┘
                                               │ Serial
                                               ▼
                                    ┌─────────────────────┐
                                    │  Arduino Mega 2560  │
                                    │  - Motor Control    │
                                    │  - Robotic Arm      │
                                    └─────────────────────┘
```

## 快速开始 / Quick Start

### 1. 硬件连接

- Arduino 通过 USB 连接树莓派（串口 `/dev/ttyACM0`）
- USB 摄像头连接树莓派
- 确保 Arduino 已烧录 `Car_Volt_Feedback_24A_with_hand_gesture_and_robo_arm.ino`

### 2. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 3. 运行机器人

```bash
# 默认配置（相机0，串口/dev/ttyACM0）
python3 main.py

# 指定相机和串口
python3 main.py 0 /dev/ttyACM0
```

## 文件说明 / File Description

### `vision.py` - 视觉系统
- **功能**：使用 USB 摄像头检测彩色小方块和竖直 A4 纸
- **核心类**：
  - `VisionSystem`: 主视觉类
  - `DetectedObject`: 检测对象数据类
- **关键方法**：
  - `detect_small_blocks()`: 检测地面小方块（红/黄/蓝）
  - `detect_sheets()`: 检测竖直 A4 纸（黑/红/黄/蓝）
  - `calculate_alignment_error()`: 计算对齐误差
  - `estimate_distance()`: 估计距离

### `car_controller.py` - 小车控制器
- **功能**：通过串口与 Arduino 通信，控制运动和机械臂
- **核心类**：`CarController`
- **运动指令**：
  - `forward(duration)`: 前进
  - `backward(duration)`: 后退
  - `turn_left(duration)`: 左转
  - `turn_right(duration)`: 右转
  - `rotate_clockwise(duration)`: 原地顺时针旋转
  - `rotate_counterclockwise(duration)`: 原地逆时针旋转
  - `stop()`: 停止
- **机械臂指令**：
  - `grab_block()`: 抓取方块（发送 "go"）
  - `release_block()`: 放下方块（发送 "rel"）

### `main.py` - 主程序与状态机
- **功能**：实现完整的自主抓取流程
- **状态机**：
  1. `FIND_START_SHEET` - 寻找黑色 A4 起点
  2. `FIND_BLOCK_AT_START` - 在起点寻找小方块
  3. `GRAB_BLOCK` - 抓取方块
  4. `GO_TO_TARGET_ZONE` - 前往目标区域（粗略导航）
  5. `ALIGN_TO_TARGET_SHEET` - 对齐目标 A4 纸
  6. `DROP_BLOCK` - 放下方块
  7. `RETURN_TO_START` - 返回起点

## 操作说明 / Controls

运行主程序时：
- **Q**: 退出程序
- **S**: 跳过当前状态（调试用）

## 串口通信协议 / Serial Protocol

发送到 Arduino 的命令（每条以 `\n` 结尾）：

| 命令 | 功能 | Arduino 函数 |
|------|------|-------------|
| `A\n` | 前进 | ADVANCE() |
| `B\n` | 后退 | BACK() |
| `L\n` | 左移/左转 | LEFT_2() |
| `R\n` | 右移/右转 | RIGHT_2() |
| `rC\n` | 顺时针旋转 | rotate_1() |
| `rA\n` | 逆时针旋转 | rotate_2() |
| `S\n` | 停止 | STOP() |
| `30\n` | 设速度30 | Motor_PWM=30 |
| `50\n` | 设速度50 | Motor_PWM=50 |
| `80\n` | 设速度80 | Motor_PWM=80 |
| `go\n` | 抓取序列 | approach+clip+rise |
| `rel\n` | 释放夹爪 | release() |

## 视觉检测原理 / Vision Detection Logic

### 区分小方块与 A4 纸

通过以下特征区分：

| 特征 | 小方块 | A4 纸 |
|------|--------|-------|
| **面积** | 300-5000 像素 | 8000-100000 像素 |
| **宽高比** | 0.5-2.0 (接近正方形) | 0.3-0.9 (竖长矩形) |
| **位置** | 画面下方 | 画面中部 |
| **颜色** | 红/黄/蓝 | 黑/红/黄/蓝 |

### HSV 颜色范围（可调整）

在 `vision.py` 中的 `color_ranges` 字典：

```python
'red': [(0, 100, 100) - (10, 255, 255),
        (160, 100, 100) - (180, 255, 255)]
'yellow': [(20, 100, 100) - (35, 255, 255)]
'blue': [(100, 100, 80) - (130, 255, 255)]
'black': [(0, 0, 0) - (180, 255, 50)]
```

## 参数调整 / Parameter Tuning

### 视觉参数 (vision.py)

```python
# 面积阈值
self.block_min_area = 300
self.block_max_area = 5000
self.sheet_min_area = 8000
self.sheet_max_area = 100000

# 宽高比范围
self.block_aspect_ratio_range = (0.5, 2.0)
self.sheet_aspect_ratio_range = (0.3, 0.9)
```

### 运动参数 (car_controller.py)

```python
# 默认运动时长
self.default_move_duration = 0.5  # 前进/后退时长
self.default_turn_duration = 0.3  # 转向时长
```

### 状态机参数 (main.py)

```python
# 超时
self.state_timeout = 30.0  # 每个状态的超时时间

# 对齐容差
self.alignment_tolerance = 30  # 像素误差容忍度
```

## 测试各模块 / Module Testing

### 测试视觉系统

```bash
python3 vision.py
```

显示实时检测结果，按键：
- **Q**: 退出
- **B**: 切换方块检测
- **S**: 切换纸张检测

### 测试小车控制

```bash
python3 car_controller.py
```

执行一系列测试动作（前进、后退、转向等）

## 工作流程 / Workflow (简化版 ⭐)

**核心改进**：移除起点检测，手动放置小车即可开始！

```
[手动放置小车在起点附近]
           │
           ▼
┌─────────────────────┐
│ 1. FIND_BLOCK       │ ← 旋转搜索附近的方块
│   (旋转搜索)        │   (红/黄/蓝任意)
└──────────┬──────────┘
           │ 发现并对齐
           ▼
┌─────────────────────┐
│ 2. GRAB_BLOCK       │ ← 串口发送 "go"
│   (机械臂抓取)      │   记录方块颜色
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. ALIGN_TO_TARGET_ │ ← 旋转搜索对应颜色 A4
│    SHEET            │   视觉伺服对齐
│   (搜索+对齐)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. DROP_BLOCK       │ ← 串口发送 "rel"
│   (放下方块)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. IDLE             │ ← 等待用户命令
│   (等待)            │   按 C 继续下一个
└─────────┬───────────┘
          │ 按 C
          └──────────→ 回到步骤 1
```

**简化优势**：
- ✅ 无需检测黑色起点纸（最易出问题的环节）
- ✅ 手动放置小车即可，位置不需要精确
- ✅ 从 7 个状态简化到 5 个状态
- ✅ 流程更稳定、更易调试
- ✅ 适合实际演示和课程项目

## 常见问题 / Troubleshooting

### 相机无法打开

```bash
# 查看可用相机
ls /dev/video*

# 测试不同编号
python3 main.py 0  # 或 1, 2...
```

### 串口连接失败

```bash
# 查看串口设备
ls /dev/tty* | grep -E "USB|ACM"

# 添加用户到 dialout 组
sudo usermod -a -G dialout $USER
# 重启后生效

# 手动指定串口
python3 main.py 0 /dev/ttyUSB0
```

### 颜色检测不准确

1. 运行 `python3 vision.py` 查看实时检测
2. 调整 `vision.py` 中的 HSV 范围
3. 改善光照条件（均匀白光最佳）

### 小车动作不符合预期

- 检查 Arduino 是否正确烧录代码
- 调整 `car_controller.py` 中的运动时长
- 确认电源充足（低电压会影响电机性能）

## 后续优化方向 / Future Improvements

- [ ] 添加 PID 控制实现平滑运动
- [ ] 使用视觉里程计改进路径规划
- [ ] 实现多方块批量抓取
- [ ] 添加异常恢复机制
- [ ] 优化状态转换逻辑
- [ ] 增加语音反馈

## 许可 / License

教育和学习用途。

---

**Have fun building your robot! 祝机器人项目成功！🤖**

