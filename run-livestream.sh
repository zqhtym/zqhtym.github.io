#!/bin/bash
# 直播流检测自动化运行脚本

set -e

# 获取当前时间戳
TIMESTAMP=$(date +%Y%m%d%H%M)
LOG_FILE="logs/livestream-${TIMESTAMP}.log"

echo "=========================================="
echo "开始直播流检测 - $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 创建日志目录
mkdir -p logs

# 记录开始时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始直播流检测" | tee -a "$LOG_FILE"

# 清理旧的输出文件
echo "清理旧的输出文件..." | tee -a "$LOG_FILE"
rm -f live+*.txt LE.txt LU.txt LE.m3u LU.m3u 2>/dev/null || true

# 运行直播流检测
echo "运行直播流检测程序..." | tee -a "$LOG_FILE"
if python3 url-check_v-txt10.py 2>&1 | tee -a "$LOG_FILE"; then
    echo "直播流检测完成" | tee -a "$LOG_FILE"
else
    echo "直播流检测失败" | tee -a "$LOG_FILE"
    exit 1
fi

# 处理输出文件
echo "处理输出文件..." | tee -a "$LOG_FILE"

# 查找生成的文件
EXCELLENT_FILE=$(ls live+excellent+*.txt 2>/dev/null | head -1)
USEFUL_FILE=$(ls live+useful+*.txt 2>/dev/null | head -1)

if [ -n "$EXCELLENT_FILE" ]; then
    echo "找到excellent文件: $EXCELLENT_FILE" | tee -a "$LOG_FILE"
    cp "$EXCELLENT_FILE" LE.txt
    echo "已复制到 LE.txt" | tee -a "$LOG_FILE"
else
    echo "未找到excellent文件" | tee -a "$LOG_FILE"
fi

if [ -n "$USEFUL_FILE" ]; then
    echo "找到useful文件: $USEFUL_FILE" | tee -a "$LOG_FILE"
    cp "$USEFUL_FILE" LU.txt
    echo "已复制到 LU.txt" | tee -a "$LOG_FILE"
else
    echo "未找到useful文件" | tee -a "$LOG_FILE"
fi

# 生成M3U文件
echo "生成M3U文件..." | tee -a "$LOG_FILE"

if [ -f "LE.txt" ] && [ -f "tools/txt_to_m3u8b.exe" ]; then
    echo "生成LE.m3u" | tee -a "$LOG_FILE"
    if tools/txt_to_m3u8b.exe LE.txt LE.m3u 2>&1 | tee -a "$LOG_FILE"; then
        echo "LE.m3u生成成功" | tee -a "$LOG_FILE"
    else
        echo "LE.m3u生成失败" | tee -a "$LOG_FILE"
    fi
else
    echo "无法生成LE.m3u: LE.txt或tools/txt_to_m3u8b.exe不存在" | tee -a "$LOG_FILE"
fi

if [ -f "LU.txt" ] && [ -f "tools/txt_to_m3u8b.exe" ]; then
    echo "生成LU.m3u" | tee -a "$LOG_FILE"
    if tools/txt_to_m3u8b.exe LU.txt LU.m3u 2>&1 | tee -a "$LOG_FILE"; then
        echo "LU.m3u生成成功" | tee -a "$LOG_FILE"
    else
        echo "LU.m3u生成失败" | tee -a "$LOG_FILE"
    fi
else
    echo "无法生成LU.m3u: LU.txt或tools/txt_to_m3u8b.exe不存在" | tee -a "$LOG_FILE"
fi

# 显示结果统计
echo "=========================================="
echo "检测结果统计:" | tee -a "$LOG_FILE"
echo "=========================================="

if [ -f "LE.txt" ]; then
    LE_COUNT=$(wc -l < LE.txt)
    echo "LE.txt (excellent): $LE_COUNT 行" | tee -a "$LOG_FILE"
fi

if [ -f "LU.txt" ]; then
    LU_COUNT=$(wc -l < LU.txt)
    echo "LU.txt (useful): $LU_COUNT 行" | tee -a "$LOG_FILE"
fi

if [ -f "LE.m3u" ]; then
    echo "LE.m3u: 已生成" | tee -a "$LOG_FILE"
fi

if [ -f "LU.m3u" ]; then
    echo "LU.m3u: 已生成" | tee -a "$LOG_FILE"
fi

# 列出所有生成的文件
echo ""
echo "生成的文件:" | tee -a "$LOG_FILE"
ls -la live+*.txt LE.txt LU.txt LE.m3u LU.m3u 2>/dev/null | tee -a "$LOG_FILE" || true

echo ""
echo "=========================================="
echo "直播流检测完成 - $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo "日志文件: $LOG_FILE"
echo ""
