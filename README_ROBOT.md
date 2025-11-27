# 技术文档

## 系统架构

```
树莓派 (Python)
  ├─ vision.py (USB相机)
  ├─ main.py (状态机)
  └─ car_controller.py (串口)
       │
       └─ Arduino (电机+机械臂)
```

## 安装

```bash
pip3 install opencv-python numpy pyserial
```

## 模块说明

### vision.py - 视觉系统

**核心类**：`VisionSystem`

**方法**：
- `detect_small_blocks(frame)` - 检测小方块
- `detect_sheets(frame, colors)` - 检测 A4 纸
- `calculate_alignment_error(obj)` - 计算对齐误差
- `estimate_distance(obj)` - 估计距离

**区分方块和 A4**：

| 特征 | 小方块 | A4 纸 |
|------|--------|-------|
| 面积 | 300-5000 | 8000-100000 |
| 宽高比 | 0.5-2.0 | 0.3-0.9 |

**HSV 颜色范围**：
```python
'red': [(0,100,100)-(10,255,255), (160,100,100)-(180,255,255)]
'yellow': [(20,100,100)-(35,255,255)]
'blue': [(100,100,80)-(130,255,255)]
```

### car_controller.py - 小车控制

**核心类**：`CarController`

**方法**：
- `forward(duration)` / `backward(duration)` - 前进/后退
- `turn_left(duration)` / `turn_right(duration)` - 转向
- `rotate_clockwise(duration)` / `rotate_counterclockwise(duration)` - 旋转
- `grab_block()` - 抓取序列
- `release_block()` - 释放

**串口协议**（波特率 9600）：

| 命令 | 功能 | Arduino 函数 |
|------|------|-------------|
| `A\n` | 前进 | ADVANCE() |
| `B\n` | 后退 | BACK() |
| `L\n` | 左移 | LEFT_2() |
| `R\n` | 右移 | RIGHT_2() |
| `rC\n` | 顺时针 | rotate_1() |
| `rA\n` | 逆时针 | rotate_2() |
| `S\n` | 停止 | STOP() |
| `go\n` | 抓取 | approach+clip+rise |
| `rel\n` | 释放 | release() |

### main.py - 状态机

**状态流程**（简化版）：

```
FIND_BLOCK → GRAB_BLOCK → ALIGN_TO_TARGET_SHEET → DROP_BLOCK → IDLE
     ↑                                                              │
     └──────────────────────── (按C继续) ──────────────────────────┘
```

**状态详情**：

1. **FIND_BLOCK**
   - 旋转搜索方块
   - 视觉对齐（水平居中）
   - 记录方块颜色

2. **GRAB_BLOCK**
   - 发送 `go` 命令
   - 等待 4 秒完成

3. **ALIGN_TO_TARGET_SHEET**
   - 旋转搜索对应颜色 A4
   - 视觉伺服对齐
   - 水平居中 + 距离调整

4. **DROP_BLOCK**
   - 发送 `rel` 命令
   - 等待 1.5 秒完成

5. **IDLE**
   - 等待用户按 C 继续

**参数**：
```python
self.state_timeout = 30.0  # 状态超时
self.max_search_attempts = 20  # 最大搜索次数
self.alignment_tolerance = 40  # 对齐容差（像素）
```

## 工作流程

```
[手动放置小车]
       ↓
[FIND_BLOCK] 旋转搜索方块
       ↓
[GRAB_BLOCK] 串口发送 "go"
       ↓
[ALIGN_TO_TARGET_SHEET] 搜索对应颜色 A4
       ↓
[DROP_BLOCK] 串口发送 "rel"
       ↓
[IDLE] 等待按 C
       ↓
   [循环]
```

## 性能优化

**问题**：同时检测所有颜色导致延迟

**解决**：根据状态按需检测
```python
if state == FIND_BLOCK:
    blocks = detect_small_blocks()  # 只检测方块
elif state == ALIGN_TO_TARGET_SHEET:
    sheets = detect_sheets(colors=[current_color])  # 只检测目标颜色
```

## 调试技巧

1. **先测试视觉**：`python3 vision.py`
2. **再测试运动**：`python3 car_controller.py`
3. **查看终端**：实时打印检测信息和串口命令
4. **调整光照**：影响最大的因素

## 常见调整

**找不到方块**：
```python
self.block_min_area = 200  # 降低
```

**找不到 A4**：
```python
self.sheet_min_area = 5000  # 降低
```

**对齐困难**：
```python
self.alignment_tolerance = 50  # 增大
```

**动作幅度**：
```python
self.default_turn_duration = 0.2  # 减小
```
