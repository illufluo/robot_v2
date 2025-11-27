# 快速上手

## 运行步骤

### 1. 场地准备
```
    [红A4]  [黄A4]  [蓝A4]  ← 竖直放置
    
         [起点区域]
       🤖 小车（手动放）
       🟥🟨🟦 方块
```

### 2. 运行
```bash
python3 main.py
```

### 3. 操作
- 自动执行：找方块→抓取→找A4→放下→等待
- **C** 继续  **Q** 退出  **R** 重置

## 终端输出示例
```
🤖 GRABBING RED BLOCK...
✓ Grab complete!

RED sheet found: error=15, distance=good
✓ Successfully aligned to RED target sheet

📦 DROPPING RED BLOCK...
✓ Block dropped successfully

🎉 TASK COMPLETED!
Press 'C' to continue
```

## 调试

### 测试视觉
```bash
python3 vision.py  # 按B切换方块，按S切换A4
```

### 测试运动
```bash
python3 car_controller.py
```

### 找不到对象？

**方块检测不到**：
```python
# vision.py
self.block_min_area = 200  # 降低阈值
```

**A4检测不到**：
```python
# vision.py  
self.sheet_min_area = 5000  # 降低阈值
```

**对齐不准**：
```python
# main.py
self.alignment_tolerance = 50  # 增加容差
```

### 相机/串口问题
```bash
ls /dev/video*  # 查看相机
python3 main.py 1  # 换相机

ls /dev/tty* | grep ACM  # 查看串口
python3 main.py 0 /dev/ttyUSB0  # 指定串口
```

## 重要提示

1. 光照要均匀（影响最大）
2. 先测试 `vision.py` 确认检测效果
3. 电量不足影响电机
4. 串口波特率 9600

