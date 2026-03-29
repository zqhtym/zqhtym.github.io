# 直播流检测工具部署指南

## 概述

本文档介绍如何将直播流检测工具部署到GitHub仓库，并通过GitHub Actions实现自动化运行。

## 部署架构

```
GitHub仓库 (zqhtym/zqhtym.github.io)
├── GitHub Actions (自动运行)
├── Ubuntu环境 (CI/CD)
├── 输出文件 (自动部署)
└── M3U文件 (自动生成)
```

## 部署步骤

### 第一步：推送代码到GitHub

1. **初始化Git仓库**
```bash
git init
git add .
git commit -m "初始化直播流检测工具"
```

2. **添加远程仓库**
```bash
git remote add origin https://github.com/zqhtym/zqhtym.github.io.git
git branch -M main
```

3. **推送代码**
```bash
git push -u origin main
```

### 第二步：配置GitHub Actions

1. **启用GitHub Pages**
   - 进入仓库设置
   - 找到Pages选项
   - 选择"Deploy from a branch"
   - 选择"main"分支和"/root"目录

2. **配置工作流**
   - 工作流文件：`.github/workflows/auto-deploy.yml`
   - 运行时间：每天北京时间3:00 (UTC 19:00)
   - 自动触发：代码推送时

3. **上传txt_to_m3u8b工具**
   - 创建GitHub Release
   - 上传`txt_to_m3u8b.exe`到`tools`目录
   - 更新工作流中的下载地址

### 第三步：Ubuntu环境配置

#### 自动安装（推荐）
```bash
# 克隆仓库
git clone https://github.com/zqhtym/zqhtym.github.io.git
cd zqhtym.github.io

# 运行安装脚本
chmod +x install-ubuntu.sh
./install-ubuntu.sh
```

#### 手动安装
```bash
# 更新系统
sudo apt-get update

# 安装基础依赖
sudo apt-get install -y python3 python3-pip python3-dev build-essential cmake

# 安装OpenCV依赖
sudo apt-get install -y libjpeg-dev libpng-dev libavcodec-dev libavformat-dev

# 安装FFmpeg
sudo apt-get install -y ffmpeg

# 安装Python依赖
pip install -r requirements.txt
```

### 第四步：本地运行测试

```bash
# 设置执行权限
chmod +x run-livestream.sh
chmod +x convert-to-m3u.sh

# 运行检测
./run-livestream.sh

# 手动转换M3U
./convert-to-m3u.sh LE.txt LE.m3u
```

## 文件说明

### 核心文件
- `url-check_v-txt10.py` - 主程序
- `video_check_worker.py` - 画面检测
- `requirements.txt` - Python依赖

### 配置文件
- `resources.m3u` - 本地M3U资源
- `resources.txt` - 本地TXT资源
- `white.txt` - 白名单配置

### 部署文件
- `.github/workflows/auto-deploy.yml` - GitHub Actions配置
- `install-ubuntu.sh` - Ubuntu安装脚本
- `run-livestream.sh` - 自动运行脚本
- `convert-to-m3u.sh` - M3U转换脚本

### 工具文件
- `tools/txt_to_m3u8b.exe` - TXT转M3U工具

## 输出文件

### 自动生成
- `live+excellent+{timestamp}.txt` - 优质直播流
- `live+wonderful+{timestamp}.txt` - 高清直播流
- `live+good+{timestamp}.txt` - 标清直播流
- `live+useful+{timestamp}.txt` - 可用直播流

### 处理后文件
- `LE.txt` - 优质流汇总 (复制自excellent)
- `LU.txt` - 可用流汇总 (复制自useful)
- `LE.m3u` - 优质流M3U格式
- `LU.m3u` - 可用流M3U格式

## 自动化流程

### GitHub Actions流程
1. **环境准备** - Ubuntu + Python + FFmpeg
2. **依赖安装** - 系统依赖 + Python包
3. **运行检测** - 执行url-check_v-txt10.py
4. **文件处理** - 复制LE.txt/LU.txt
5. **M3U转换** - 生成LE.m3u/LU.m3u
6. **自动部署** - 推送到GitHub Pages

### 定时任务
- **运行时间**: 每天北京时间3:00
- **时区设置**: UTC 19:00 (cron: '0 19 * * *')
- **手动触发**: 支持workflow_dispatch

## 监控和日志

### 日志文件
- `logs/livestream-{timestamp}.log` - 运行日志
- GitHub Actions运行日志 - 在线查看

### 监控指标
- 检测条目数量
- 有效流数量
- 运行时间
- 错误信息

## 故障排除

### 常见问题

1. **FFmpeg未安装**
```bash
# 检查FFmpeg
ffmpeg -version

# 重新安装
sudo apt-get install -y ffmpeg
```

2. **OpenCV安装失败**
```bash
# 安装OpenCV依赖
sudo apt-get install -y libopencv-dev python3-opencv

# 或使用pip安装
pip install opencv-python
```

3. **txt_to_m3u8b.exe不存在**
```bash
# 检查文件
ls -la tools/txt_to_m3u8b.exe

# 手动上传到tools目录
```

4. **权限问题**
```bash
# 设置执行权限
chmod +x *.sh
chmod +x tools/*.exe
```

### 调试方法

1. **查看GitHub Actions日志**
   - 进入仓库Actions页面
   - 查看具体运行记录

2. **本地调试**
```bash
# 本地运行测试
python3 url-check_v-txt10.py

# 查看详细日志
./run-livestream.sh 2>&1 | tee debug.log
```

3. **检查依赖**
```bash
# 检查Python包
pip list

# 检查系统工具
which ffmpeg ffprobe
```

## 性能优化

### 系统配置
- **CPU**: 多核处理器 (建议4核以上)
- **内存**: 至少2GB RAM
- **存储**: 至少10GB可用空间
- **网络**: 稳定的互联网连接

### 程序配置
- **进程数**: 根据CPU核心数调整
- **超时设置**: 根据网络情况调整
- **并发限制**: 避免过度并发

## 安全考虑

### 访问控制
- **仓库权限**: 设置适当的访问权限
- **API密钥**: 使用GitHub Secrets管理
- **文件权限**: 设置适当的文件权限

### 数据保护
- **敏感信息**: 避免在代码中硬编码
- **日志清理**: 定期清理旧日志
- **备份策略**: 定期备份重要数据

## 维护指南

### 定期维护
1. **更新依赖**: 定期更新Python包
2. **清理日志**: 清理旧的日志文件
3. **监控运行**: 检查自动化运行状态
4. **更新配置**: 根据需要调整配置

### 版本更新
1. **测试新版本**: 在本地测试新版本
2. **更新文档**: 更新相关文档
3. **部署更新**: 推送到GitHub触发自动部署
4. **验证结果**: 检查更新后的运行结果

## 联系支持

如果遇到问题，请：
1. 查看本文档的故障排除部分
2. 检查GitHub Issues
3. 提交新的Issue描述问题
4. 提供详细的错误日志和系统信息
