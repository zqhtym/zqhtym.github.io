# GitHub Actions 内存优化方案

## 问题分析

### 内存崩溃原因
```
malloc(): invalid size (unsorted)
Error: Process completed with exit code 134.
```

### 崩溃时机
- **画面检测阶段**: 80/1944 检测时崩溃
- **媒体信息分析**: MediaInfo分析超时后崩溃
- **内存溢出**: GitHub Actions 2GB内存限制被突破

## 优化策略

### 1. 内存限制优化

#### **系统级限制**
```bash
# 优化前
ulimit -v 4194304  # 4GB虚拟内存

# 优化后
ulimit -v 3145728  # 3GB虚拟内存 (-25%)
ulimit -m 2097152  # 2GB常驻内存 (新增)
```

#### **Python内存优化**
```python
# 垃圾回收优化
gc.set_threshold(700, 10, 5)  # 更频繁的垃圾回收

# 环境变量
export MALLOC_TRIM_THRESHOLD_=100000  # 内存分配优化
```

### 2. 并发控制优化

#### **线程数减少**
```python
# 优化前
max_threads = 3  # 3个并发线程

# 优化后
max_threads = 2  # 2个并发线程 (-33%)
```

#### **分批处理**
```python
# 新增分批机制
batch_size = 100  # 每批处理100个条目

for i in range(0, len(items), batch_size):
    batch = items[i:i+batch_size]
    process_batch(batch)
    gc.collect()  # 每批后强制垃圾回收
```

### 3. 内存监控机制

#### **实时监控**
```python
import psutil

memory_percent = psutil.virtual_memory().percent
print(f"[内存监控] 当前内存使用: {memory_percent:.1f}%")

if memory_percent > 80:
    print("[内存警告] 内存使用过高，暂停5秒")
    time.sleep(5)
    gc.collect()
```

#### **内存阈值**
- **警告阈值**: 80%
- **暂停时间**: 5秒
- **强制回收**: 暂停后立即垃圾回收

### 4. 垃圾回收优化

#### **关键节点回收**
```python
# 在每个主要步骤后强制回收
gc.collect()  # 资源加载后
gc.collect()  # 去重后  
gc.collect()  # 过滤后
gc.collect()  # 404检测后
gc.collect()  # 速度测试后
gc.collect()  # 每批画面检测后
gc.collect()  # 最终回收
```

#### **回收参数调整**
```python
# 优化前
gc.set_threshold(700, 10, 10)

# 优化后  
gc.set_threshold(700, 10, 5)  # 更频繁的回收
```

## 实现方案

### 1. 代码优化

#### **分批处理逻辑**
```python
def check_video_validity_batch(items, max_threads=2, batch_size=100):
    """分批处理画面检测以避免内存溢出"""
    video_valid_items = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        print(f"【画面检测批次】{i//batch_size + 1} | 本批数量: {len(batch)}")
        
        batch_results = check_video_validity(batch, max_threads=max_threads)
        video_valid_items.extend(batch_results)
        
        # 内存管理
        gc.collect()
        monitor_memory()
    
    return video_valid_items
```

#### **内存监控函数**
```python
def monitor_memory():
    """监控内存使用情况"""
    try:
        import psutil
        memory_percent = psutil.virtual_memory().percent
        print(f"[内存监控] 当前内存使用: {memory_percent:.1f}%")
        
        if memory_percent > 80:
            print("[内存警告] 内存使用过高，暂停5秒")
            time.sleep(5)
            gc.collect()
            
        return memory_percent
    except ImportError:
        print("[内存监控] psutil未安装，跳过监控")
        return 0
```

### 2. 环境配置

#### **GitHub Actions配置**
```yaml
- name: 运行直播流检测
  run: |
    # 内存限制
    ulimit -v 3145728  # 3GB虚拟内存
    ulimit -m 2097152  # 2GB常驻内存
    
    # Python优化
    export PYTHONOPTIMIZE=1
    export PYTHONHASHSEED=0
    export MALLOC_TRIM_THRESHOLD_=100000
    
    # 垃圾回收设置
    python -c "import gc; gc.set_threshold(700, 10, 5)"
    
    # 运行程序
    python url-check_v-pro.py
```

#### **依赖更新**
```txt
# requirements.txt
opencv-python>=4.8.0
pytz>=2023.3
pymediainfo>=6.0.1
numpy>=1.24.0
psutil>=5.9.0  # 新增：内存监控
requests>=2.31.0
urllib3>=2.0.0
```

## 预期效果

### 内存使用优化
| 优化项目 | 优化前 | 优化后 | 改善幅度 |
|---------|--------|--------|----------|
| 虚拟内存限制 | 4GB | 3GB | -25% |
| 常驻内存限制 | 无限制 | 2GB | 新增限制 |
| 并发线程数 | 3 | 2 | -33% |
| 批处理大小 | 全量 | 100 | 分批处理 |

### 稳定性提升
- **内存溢出**: 通过分批处理避免
- **垃圾回收**: 更频繁的内存清理
- **实时监控**: 及时发现内存问题
- **自动暂停**: 内存过高时自动暂停

### 性能影响
- **处理时间**: 可能增加10-20%（分批处理开销）
- **内存使用**: 控制在2GB以内
- **稳定性**: 显著提升，避免崩溃

## 监控指标

### 关键指标
1. **内存使用率**: 峰值不超过80%
2. **垃圾回收频率**: 每批处理后
3. **批次处理时间**: 监控每批耗时
4. **崩溃率**: 目标为0%

### 日志示例
```
【画面检测批次】1/20 | 本批数量: 100
[内存监控] 当前内存使用: 65.2%
【画面检测批次】2/20 | 本批数量: 100  
[内存监控] 当前内存使用: 72.8%
[内存警告] 内存使用过高，暂停5秒
[内存监控] 当前内存使用: 68.1%
```

## 故障排除

### 常见问题
1. **内存仍然溢出**: 进一步减少batch_size
2. **处理速度过慢**: 适当增加batch_size
3. **监控失败**: 确保psutil正确安装

### 调试方法
```bash
# 手动设置内存限制
ulimit -v 3145728
ulimit -m 2097152

# 监控内存使用
watch -n 1 'free -h'

# 运行程序
python url-check_v-pro.py
```

## 持续优化

### 监控策略
1. **实时监控**: 每批检查内存使用
2. **阈值调整**: 根据实际情况调整
3. **批次优化**: 动态调整批次大小

### 优化方向
1. **智能批次**: 根据内存使用动态调整
2. **预测算法**: 预测内存使用峰值
3. **缓存管理**: 优化缓存使用策略

## 总结

通过多层次的内存优化策略，预期可以解决GitHub Actions环境下的内存崩溃问题：

1. **系统级限制**: 3GB虚拟内存 + 2GB常驻内存
2. **并发控制**: 2线程 + 分批处理
3. **内存监控**: 实时监控 + 自动暂停
4. **垃圾回收**: 更频繁的内存清理

这种方案既保证了程序能够稳定运行，又通过分批处理确保了所有条目都能被检测，是一个平衡性能和稳定性的优化方案。
