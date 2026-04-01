# IPTV直播流检测工具

基于IPTV API框架的高效直播流检测工具，支持大规模并发检测和内存优化。

## 🚀 特性

- **基于IPTV API框架**: 采用经过验证的稳定架构
- **异步并发检测**: 高效的异步网络检测
- **智能内存管理**: 基于IPTV API的内存优化策略
- **多阶段检测**: URL有效性 → 视频检测 → 速度测试
- **GitHub Actions支持**: 自动化部署和检测
- **结果分类**: 按速度和质量自动分类

## 📋 检测流程

1. **URL有效性检测**: 检查链接是否可访问
2. **视频有效性检测**: 检查是否包含有效视频流
3. **速度测试**: 测试实际下载速度
4. **结果分类**: 按速度自动分类输出

## 🛠️ 安装和使用

### 本地运行

```bash
# 克隆项目
git clone <repository-url>
cd iptv-check-master

# 安装依赖
pip install -r requirements.txt

# 准备源文件
echo "央视1,http://example.com/cctv1.m3u8" > resources.txt

# 运行检测
python main.py
```

### 配置文件

编辑 `config/config.ini` 文件：

```ini
[Settings]
source_file = resources.txt
output_dir = output
open_url_check = True
open_video_check = True
open_speed_test = True
max_concurrent = 10
batch_size = 50
memory_threshold = 80
```

## 📊 输出结果

检测结果会按速度分类输出到 `output/` 目录：

- `live+excellent+{timestamp}.txt` - 速度 > 1MB/s (央视)
- `live+wonderful+{timestamp}.txt` - 速度 > 700KB/s (卫视)  
- `live+good+{timestamp}.txt` - 速度 > 500KB/s (港澳台)
- `live+useful+{timestamp}.txt` - 速度 > 200KB/s (其它)

## 🔧 技术特性

### IPTV API框架优势

- **稳定架构**: 基于成功运行的IPTV API框架
- **内存优化**: 智能缓存和垃圾回收机制
- **并发控制**: 信号量控制防止资源竞争
- **批次处理**: 分批处理避免内存溢出

### 异步检测

```python
# IPTV API风格的并发控制
semaphore = asyncio.Semaphore(max_concurrent)

async def check_url(url):
    async with semaphore:
        # 检测逻辑
        pass

# 批量并发执行
tasks = [check_url(url) for url in urls]
results = await asyncio.gather(*tasks)
```

### 内存管理

```python
# IPTV API风格的内存管理
def check_memory():
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > threshold:
        # 多轮垃圾回收
        for i in range(3):
            gc.collect()
            await asyncio.sleep(0.1)
```

## 🌍 GitHub Actions

项目配置了自动化GitHub Actions工作流：

- **定时运行**: 每天北京时间8:00自动检测
- **资源限制**: 严格的内存和CPU限制
- **自动部署**: 结果自动部署到GitHub Pages
- **构建产物**: 自动上传检测结果

## 📁 项目结构

```
iptv-check-master/
├── main.py                    # 主程序
├── config/
│   └── config.ini            # 配置文件
├── utils/
│   ├── config.py             # 配置管理
│   ├── types.py              # 类型定义
│   ├── tools.py              # 工具函数
│   ├── url_check.py          # URL检测
│   ├── video_check.py        # 视频检测
│   ├── video_check_worker.py # 画面检测worker
│   └── video_check_worker_github.py # GitHub优化版本
├── .github/workflows/
│   └── auto-deploy.yml       # GitHub Actions工作流
├── requirements.txt          # Python依赖
└── README.md                # 说明文档
```

## 🔍 检测原理

### URL有效性检测
- 使用HEAD请求检查链接可访问性
- 支持HTTP/HTTPS/RTSP/RTMP等协议
- 智能超时控制和错误处理

### 视频有效性检测
- 使用FFmpeg检测视频流
- 检查画面变化和音频轨道
- 支持多种视频格式和编码

### 速度测试
- 下载前1MB数据测试实际速度
- 计算平均下载速度和延迟
- 按速度自动分类排序

## 📈 性能优化

### 并发控制
- 使用信号量控制并发数量
- 防止过多连接导致服务器拒绝
- 智能批次处理避免内存溢出

### 内存管理
- 基于IPTV API的智能缓存机制
- 多轮垃圾回收释放内存
- 深拷贝避免内存污染

### 错误处理
- 完善的异常捕获和处理
- 智能重试和降级机制
- 详细的错误日志和统计

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目。

## 📄 许可证

本项目基于MIT许可证开源。

## 🙏 致谢

- [IPTV-API](https://github.com/Guovin/iptv-api) - 提供稳定的框架基础
- [FFmpeg](https://ffmpeg.org/) - 强大的多媒体处理工具
- [OpenCV](https://opencv.org/) - 计算机视觉库
