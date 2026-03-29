#!/bin/bash
# M3U转换脚本 - 将TXT格式转换为M3U格式

set -e

# 检查参数
if [ $# -lt 2 ]; then
    echo "用法: $0 <输入TXT文件> <输出M3U文件> [组名]"
    echo "示例: $0 LE.txt LE.m3u '优质直播'"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"
GROUP_NAME="${3:-直播流}"

# 检查输入文件
if [ ! -f "$INPUT_FILE" ]; then
    echo "错误: 输入文件 $INPUT_FILE 不存在"
    exit 1
fi

# 检查转换工具
if [ ! -f "tools/txt_to_m3u8b.exe" ]; then
    echo "错误: 转换工具 tools/txt_to_m3u8b.exe 不存在"
    echo "请确保已上传txt_to_m3u8b.exe到tools目录"
    exit 1
fi

echo "=========================================="
echo "开始转换M3U文件"
echo "=========================================="
echo "输入文件: $INPUT_FILE"
echo "输出文件: $OUTPUT_FILE"
echo "组名: $GROUP_NAME"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 使用txt_to_m3u8b工具转换
echo "使用txt_to_m3u8b工具转换..."
if tools/txt_to_m3u8b.exe "$INPUT_FILE" "$OUTPUT_FILE"; then
    echo "转换成功!"
else
    echo "转换失败，尝试手动生成M3U文件..."
    
    # 手动生成M3U文件
    echo "#EXTM3U" > "$OUTPUT_FILE"
    
    # 读取TXT文件并转换为M3U格式
    while IFS=',' read -r name url || [ -n "$name" ]; do
        # 跳过空行和注释行
        if [ -z "$name" ] || [[ "$name" == \#* ]]; then
            continue
        fi
        
        # 去除前后空格
        name=$(echo "$name" | xargs)
        url=$(echo "$url" | xargs)
        
        # 跳过无效行
        if [ -z "$name" ] || [ -z "$url" ]; then
            continue
        fi
        
        # 写入M3U格式
        echo "#EXTINF:-1,$name" >> "$OUTPUT_FILE"
        echo "$url" >> "$OUTPUT_FILE"
        
    done < "$INPUT_FILE"
    
    echo "手动生成M3U文件完成"
fi

# 验证输出文件
if [ -f "$OUTPUT_FILE" ]; then
    LINE_COUNT=$(wc -l < "$OUTPUT_FILE")
    echo "=========================================="
    echo "转换完成!"
    echo "输出文件: $OUTPUT_FILE"
    echo "总行数: $LINE_COUNT"
    echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    
    # 显示前几行内容预览
    echo ""
    echo "文件预览 (前10行):"
    head -10 "$OUTPUT_FILE" 2>/dev/null || true
else
    echo "错误: 输出文件 $OUTPUT_FILE 未生成"
    exit 1
fi
