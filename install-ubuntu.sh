#!/bin/bash
# Ubuntu系统依赖安装脚本
# 用于部署直播流检测工具

set -e

echo "=========================================="
echo "开始安装Ubuntu系统依赖"
echo "=========================================="

# 更新系统包
echo "更新系统包..."
sudo apt-get update

# 安装基础开发工具
echo "安装基础开发工具..."
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    git \
    wget \
    unzip \
    curl

# 安装Python开发环境
echo "安装Python开发环境..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv

# 安装OpenCV依赖
echo "安装OpenCV依赖..."
sudo apt-get install -y \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libgtk-3-dev \
    libatlas-base-dev \
    gfortran

# 安装FFmpeg
echo "安装FFmpeg..."
sudo apt-get install -y ffmpeg

# 验证FFmpeg安装
echo "验证FFmpeg安装..."
ffmpeg -version
ffprobe -version

# 升级pip
echo "升级pip..."
python3 -m pip install --upgrade pip

# 安装Python依赖
echo "安装Python依赖..."
if [ -f "requirements.txt" ]; then
    python3 -m pip install -r requirements.txt
else
    echo "警告: requirements.txt文件不存在"
fi

# 创建工具目录
echo "创建工具目录..."
mkdir -p tools

# 下载txt_to_m3u8b工具 (需要预先上传到可访问位置)
echo "下载txt_to_m3u8b工具..."
# 这里需要替换为实际的下载地址
if [ ! -f "tools/txt_to_m3u8b.exe" ]; then
    echo "请手动上传txt_to_m3u8b.exe到tools目录"
    echo "或修改此脚本中的下载地址"
fi

# 设置执行权限
chmod +x tools/txt_to_m3u8b.exe 2>/dev/null || true

# 创建日志目录
echo "创建日志目录..."
mkdir -p logs

echo "=========================================="
echo "Ubuntu系统依赖安装完成"
echo "=========================================="
echo ""
echo "下一步:"
echo "1. 确保txt_to_m3u8b.exe已上传到tools目录"
echo "2. 运行 ./run-livestream.sh 开始检测"
echo ""
