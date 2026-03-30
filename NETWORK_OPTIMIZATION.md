# GitHub Actions 网络环境优化方案

## 问题分析

### 网络环境差异
| 环境类型 | 内网环境 | GitHub Actions(外网) |
|---------|----------|-------------------|
| 网络延迟 | <50ms | 200-500ms |
| 带宽限制 | 无 | 可能受限 |
| 连接稳定性 | 高 | 中等 |
| 防火墙 | 无 | 可能有 |
| 访问权限 | 无限制 | 可能有限制 |

### 检测效果对比
- **内网环境**: 有效率 30-50%
- **GitHub Actions**: 有效率 9.5% (过低)

## 优化策略

### 1. 网络容错优化

#### **增加超时时间**
```python
# 标准配置
TIMEOUT = {
    'video_check': 15,      # 15秒
    'video_total_timeout': 180  # 3分钟
}

# GitHub Actions优化配置
TIMEOUT = {
    'video_check': 20,      # 20秒 (+33%)
    'video_total_timeout': 240  # 4分钟 (+33%)
}
```

#### **添加重试机制**
```python
'retry_count': 2,          # 重试2次
# 指数退避策略: 1s, 2s, 4s
```

#### **网络容错率**
```python
'network_tolerance': 0.3,  # 30%网络容错
```

### 2. 检测参数调整

#### **降低检测要求**
```python
# 标准配置
'min_diff': 1000,          # 帧差异阈值
'min_frames': 3,          # 最少帧数
'max_frames': 8,           # 最多帧数

# GitHub Actions优化配置
'min_diff': 500,           # 降低50%
'min_frames': 2,           # 减少要求
'max_frames': 5,           # 减少负载
```

#### **降低采样频率**
```python
'frame_interval': 2,       # 2秒采样（减少网络压力）
```

#### **关闭音频检测**
```python
'audio_check': False,       # 减少复杂性
```

### 3. 环境自动检测

#### **检测逻辑**
```python
def detect_environment():
    is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    
    if is_github_actions:
        return 'video_check_worker_github.py'
    else:
        return 'video_check_worker.py'
```

#### **自动切换**
- **GitHub Actions**: 使用外网优化版本
- **本地环境**: 使用标准版本
- **回退机制**: 自动版本兜底

## 实现方案

### 文件结构
```
url-check_v-pro.py              # 主程序
├── video_check_worker.py        # 标准版本（内网）
├── video_check_worker_github.py # 优化版本（外网）
└── video_check_worker_auto.py   # 自动检测版本
```

### 配置对比

#### **标准版本 (内网)**
```python
VIDEO_CHECK = {
    'frame_interval': 1,      # 1秒采样
    'min_diff': 1000,         # 1000阈值
    'min_frames': 3,          # 3帧对比
    'max_frames': 8,          # 8帧上限
    'audio_check': True,      # 音频检测
    'retry_count': 0          # 无重试
}
```

#### **GitHub Actions版本 (外网)**
```python
VIDEO_CHECK = {
    'frame_interval': 2,      # 2秒采样（降频）
    'min_diff': 500,          # 500阈值（降50%）
    'min_frames': 2,          # 2帧对比（降要求）
    'max_frames': 5,          # 5帧上限（降负载）
    'audio_check': False,     # 关闭音频检测
    'retry_count': 2,         # 2次重试
    'network_tolerance': 0.3  # 30%容错
}
```

## 预期效果

### 有效率提升
| 环境 | 当前有效率 | 优化后预期 | 提升幅度 |
|------|-----------|-----------|----------|
| GitHub Actions | 9.5% | 25-35% | +160%~270% |
| 本地环境 | 30-50% | 保持不变 | 0% |

### 性能优化
- **网络延迟适应**: 增加超时和重试
- **检测精度平衡**: 降低阈值但保持准确性
- **资源使用优化**: 减少帧数和音频检测

### 稳定性提升
- **容错机制**: 网络波动自动处理
- **回退策略**: 多版本自动切换
- **错误恢复**: 指数退避重试

## 使用方法

### 自动模式（推荐）
```python
# 主程序会自动检测环境
python url-check_v-pro.py
```

### 手动指定
```python
# 强制使用GitHub Actions版本
export GITHUB_ACTIONS=true
python url-check_v-pro.py

# 强制使用标准版本
unset GITHUB_ACTIONS
python url-check_v-pro.py
```

## 监控指标

### 关键指标
1. **有效率**: 检测成功/总检测
2. **平均耗时**: 单个检测时间
3. **网络超时率**: 网络相关失败
4. **重试成功率**: 重试后成功比例

### 日志示例
```
[环境检测] 使用GitHub Actions优化版本 | URL: http://example.com/stream
[调试] 网络错误，重试 1/2
[调试] 画面变化检测成功（外网） | URL: http://example.com/stream | 读取帧数: 15 | 有效对比帧数: 3 | 平均帧差异: 1200 | 变化: True
```

## 故障排除

### 常见问题
1. **网络超时**: 增加重试次数
2. **检测失败**: 降低检测要求
3. **性能问题**: 减少并发线程

### 调试方法
```bash
# 模拟网络延迟
export SIMULATE_NETWORK_DELAY=0.5

# 强制使用特定版本
export FORCE_WORKER_VERSION=github

# 启用详细日志
export DEBUG_VIDEO_CHECK=true
```

## 持续优化

### 监控策略
1. **定期检查**: 每周分析有效率
2. **A/B测试**: 对比不同配置效果
3. **参数调优**: 根据实际数据调整

### 优化方向
1. **智能阈值**: 根据网络状况动态调整
2. **预测算法**: 预测网络最佳检测时机
3. **缓存机制**: 缓存检测结果减少重复检测

## 总结

通过针对GitHub Actions外网环境的专门优化，预期可以将画面检测的有效率从9.5%提升到25-35%，同时保持本地环境的检测效果。主要优化策略包括：

1. **网络容错**: 增加超时、重试、容错机制
2. **参数调优**: 降低检测要求，适应网络波动
3. **环境适配**: 自动检测并选择最佳策略
4. **性能平衡**: 在准确性和效率间找到最佳平衡点

这种方案既解决了GitHub Actions环境下的检测问题，又保持了本地环境的检测效果，实现了环境自适应的优化策略。
