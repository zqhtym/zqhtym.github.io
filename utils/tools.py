#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模块 - 基于IPTV API框架
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def get_pbar_remaining(n: int, total: int, start_time: float) -> str:
    """获取进度条剩余时间"""
    if n == 0:
        return "计算中..."
    
    elapsed = time.time() - start_time
    if elapsed <= 0:
        return "计算中..."
    
    rate = n / elapsed
    remaining = (total - n) / rate if rate > 0 else 0
    
    hours = int(remaining // 3600)
    minutes = int((remaining % 3600) // 60)
    seconds = int(remaining % 60)
    
    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    elif minutes > 0:
        return f"{minutes}分钟{seconds}秒"
    else:
        return f"{seconds}秒"


def get_ip_address() -> str:
    """获取本机IP地址"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def convert_to_m3u(channels: List[str], output_file: str = "output.m3u"):
    """转换为M3U格式"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for channel in channels:
                if "," in channel:
                    name, url = channel.split(",", 1)
                    f.write(f"#EXTINF:-1,{name}\n{url}\n")
        return True
    except Exception as e:
        print(f"转换M3U失败: {e}")
        return False


def format_interval(seconds: float) -> str:
    """格式化时间间隔"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}分{secs:.1f}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}小时{minutes}分{secs:.1f}秒"


def resource_path(relative_path: str, persistent: bool = False) -> str:
    """获取资源路径"""
    try:
        base_path = sys._MEIPASS if persistent and hasattr(sys, '_MEIPASS') else os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    except Exception:
        return os.path.abspath(relative_path)


def get_urls_from_file(file_path: str) -> List[str]:
    """从文件获取URL列表"""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)
    except Exception as e:
        print(f"读取URL文件失败: {e}")
    return urls


def get_version_info() -> str:
    """获取版本信息"""
    return "1.0.0"


def update_file(source: str, target: str):
    """更新文件"""
    try:
        import shutil
        shutil.copy2(source, target)
        print(f"文件更新成功: {source} -> {target}")
    except Exception as e:
        print(f"文件更新失败: {e}")


def ensure_dir(path: str) -> bool:
    """确保目录存在"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建目录失败: {e}")
        return False


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_speed(speed_bytes: float) -> str:
    """格式化速度"""
    if speed_bytes < 1024:
        return f"{speed_bytes:.1f} B/s"
    elif speed_bytes < 1024 * 1024:
        return f"{speed_bytes / 1024:.1f} KB/s"
    else:
        return f"{speed_bytes / (1024 * 1024):.1f} MB/s"


def get_current_timestamp() -> str:
    """获取当前时间戳"""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def sanitize_filename(filename: str) -> str:
    """清理文件名"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()


def is_valid_url(url: str) -> bool:
    """检查URL是否有效"""
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    if not url:
        return False
    
    valid_schemes = ['http://', 'https://', 'rtsp://', 'rtmp://', 'rtp://']
    return any(url.startswith(scheme) for scheme in valid_schemes)


def extract_url_info(url: str) -> dict:
    """提取URL信息"""
    info = {
        'scheme': '',
        'host': '',
        'port': '',
        'path': '',
        'query': '',
        'fragment': ''
    }
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        info['scheme'] = parsed.scheme
        info['host'] = parsed.hostname or ''
        info['port'] = str(parsed.port) if parsed.port else ''
        info['path'] = parsed.path
        info['query'] = parsed.query
        info['fragment'] = parsed.fragment
    except:
        pass
    
    return info
