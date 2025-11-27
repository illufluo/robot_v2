# 快速上手指南 / Quick Start Guide

## 🚀 5分钟快速开始

### 1. 硬件准备

- ✅ Arduino 已烧录代码并通过 USB 连接树莓派
- ✅ USB 摄像头已连接
- ✅ 小车和机械臂已连接到 Arduino
- ✅ 电源充足

### 2. 场地布置

```
              [红色 A4]
                 |
                 |
    [黄色 A4] --+-- [蓝色 A4]
                 |
                 |
           [起点区域]
         🤖 (手动放置小车)
         🟥🟦🟨 (放置一些方块)
```

**注意**：
- 3 张竖直的彩色 A4 纸要在摄像头视野范围内（可以分散放置）
- 小方块放在小车附近的地面上
- **不需要**黑色起点纸

### 3. 运行程序

```bash
cd /Users/chenyanning/Desktop/vision
python3 main.py
```

程序会显示：
```
🤖 SIMPLIFIED BLOCK PICKING ROBOT
Workflow:
  1. Find nearby block (RED/YELLOW/BLUE)
  2. Grab the block
  3. Find matching colored sheet
  4. Drop the block
  5. Wait for next command

Press ENTER to start...
```

### 4. 执行流程

**自动执行**：
1. ⏳ 小车旋转搜索附近的方块
2. 🎯 对齐到方块（水平居中）
3. 🤖 抓取方块（机械臂动作）
4. 🔄 旋转搜索对应颜色的 A4 纸
5. 🎯 对齐到 A4 纸
6. 📦 放下方块
7. ⏸️ 进入 IDLE 状态

**终端输出示例**：
```
==================================================
STATE: FIND_BLOCK -> GRAB_BLOCK
==================================================

==================================================
🤖 GRABBING RED BLOCK...
==================================================
Sent command: go
✓ Grab complete!
  Total blocks processed: 1

==================================================
STATE: GRAB_BLOCK -> ALIGN_TO_TARGET_SHEET
==================================================

RED sheet found: error=15, distance=good
✓ Successfully aligned to RED target sheet

==================================================
📦 DROPPING RED BLOCK...
==================================================
✓ Block dropped successfully at RED zone

==================================================
🎉 TASK COMPLETED!
   Total blocks processed: 1
==================================================

Options:
  - Press 'C' to continue with next block
  - Press 'Q' to quit
```

### 5. 继续运行

- **按 C** - 继续抓取下一个方块
- **按 Q** - 退出程序
- **按 R** - 强制重置到 FIND_BLOCK 状态

### 6. 可视化窗口

OpenCV 窗口实时显示：
- 🟥 小方块：红色矩形框
- 🟦 A4 纸：蓝色粗矩形框
- 🎯 绿色十字：画面中心
- 📊 状态信息：当前状态、方块颜色、完成数量

---

## ⚙️ 常见调整

### 如果找不到方块

1. **检查光照** - 确保光线均匀
2. **调整相机角度** - 俯视角度最佳
3. **调整 HSV 范围** - 编辑 `vision.py` 的 `color_ranges`
4. **降低面积阈值** - 如果方块太小

```python
# vision.py
self.block_min_area = 200  # 默认 300，可以降低
```

### 如果找不到 A4 纸

1. **检查 A4 是否竖直放置**
2. **增大 A4 纸面积阈值范围**

```python
# vision.py
self.sheet_min_area = 5000  # 默认 8000，可以降低
```

### 如果对齐不准

1. **增加对齐容差**

```python
# main.py
self.alignment_tolerance = 50  # 默认 40，增加容差
```

2. **调整运动时长**

```python
# car_controller.py
self.default_turn_duration = 0.2  # 默认 0.3，减小转向幅度
```

---

## 🐛 调试技巧

### 1. 先测试视觉系统

```bash
python3 vision.py
```

- 按 **B** 切换方块检测开关
- 按 **S** 切换 A4 纸检测开关
- 观察检测框是否正确

### 2. 再测试小车控制

```bash
python3 car_controller.py
```

会自动执行一系列测试动作。

### 3. 查看终端输出

程序会实时打印：
- 检测到的对象信息
- 对齐误差值
- 距离估计
- 发送的串口命令

### 4. 调整串口设备

如果提示串口连接失败：

```bash
# 查看可用串口
ls /dev/tty* | grep -E "USB|ACM"

# 指定串口运行
python3 main.py 0 /dev/ttyUSB0
```

---

## 📝 工作流程图

```
[开始]
  ↓
[手动放置小车在起点]
  ↓
[运行 python3 main.py]
  ↓
┌─────────────────────┐
│  FIND_BLOCK         │ ← 旋转搜索方块
│  (旋转搜索)         │
└─────────┬───────────┘
          │ 发现方块
          ↓
┌─────────────────────┐
│  对齐到方块         │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│  GRAB_BLOCK         │ ← 发送 "go" 命令
│  (机械臂抓取)       │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│  ALIGN_TO_TARGET_   │ ← 旋转搜索对应颜色 A4
│  SHEET              │   视觉伺服对齐
│  (旋转搜索+对齐)    │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│  DROP_BLOCK         │ ← 发送 "rel" 命令
│  (放下方块)         │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│  IDLE               │ ← 等待用户命令
│  (按 C 继续)        │
└─────────┬───────────┘
          │ 按 C
          └──────────→ [回到 FIND_BLOCK]
```

---

## 💡 重要提示

1. **首次运行**建议先用 `python3 vision.py` 测试视觉检测效果
2. **光照条件**对检测影响很大，建议在均匀光照下使用
3. **电池电量**不足会导致电机无力，影响运动效果
4. **串口波特率**必须与 Arduino 代码匹配（默认 9600）
5. 如果小车动作异常，检查 Arduino 是否正确烧录代码

---

**祝使用顺利！🎉**

有问题请查看 `README.md` 或 `README_ROBOT.md` 的详细说明。

