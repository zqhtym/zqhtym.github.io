#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV直播流检测工具 - 基于IPTV API框架
Author: chaichunyang@outlook.com
"""

import asyncio
import copy
import os
import sys
import time as time_module
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union, Optional
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
from functools import partial
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import multiprocessing

from tqdm import tqdm

# 全局函数，用于多进程
def test_speed_worker_global(resource, progress_dict):
    """速度测试工作进程（全局函数，可序列化）"""
    
    class Downloader:
        """测速类"""
        def __init__(self, url):
            self.url = url
            self.startTime = time_module.time()
            self.recive = 0
            self.endTime = None

        def getSpeed(self):
            """计算速度（bytes/s）"""
            if self.endTime and self.recive != -1 and (self.endTime - self.startTime) > 0:
                return self.recive / (self.endTime - self.startTime)
            else:
                return -1

    def getStreamUrl(m3u8: str, depth: int = 1):
        """解析 M3U8 流地址"""
        MAX_RECURSION_DEPTH = 2
        urls = []
        if depth > MAX_RECURSION_DEPTH:
            return urls
        try:
            req = Request(m3u8, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urlopen(req, timeout=5) as resp:
                content = resp.read().decode('utf-8', errors='ignore')
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if line.startswith('http'):
                            urls.append(line)
                        elif line.startswith('/'):
                            base_url = m3u8.rsplit('/', 1)[0]
                            urls.append(base_url + line)
                        else:
                            base_url = m3u8.rsplit('/', 1)[0]
                            urls.append(base_url + '/' + line)
        except Exception:
            pass
        return urls

    def downloadTester(downloader):
        """下载测试器"""
        try:
            url = downloader.url
            if url.lower().endswith(('.flv', '.mp4', '.ts', '.mkv', '.avi', '.mov')):
                stream_urls = [url]
            else:
                stream_urls = getStreamUrl(url)
            
            if not stream_urls:
                downloader.recive = -1
                downloader.endTime = time_module.time()
                return
            
            req = Request(stream_urls[0], headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urlopen(req, timeout=5) as resp:
                chunk_size = 10240
                while time_module.time() - downloader.startTime < 3:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    downloader.recive += len(chunk)
                    if downloader.recive // chunk_size >= 10:
                        if time_module.time() - downloader.startTime >= 3:
                            break
        except Exception:
            downloader.recive = -1
        finally:
            downloader.endTime = time_module.time()
    
    try:
        # 解析流地址
        stream_urls = []
        url = resource.get('url', '')
        if url.lower().endswith(('.flv', '.mp4', '.ts', '.mkv', '.avi', '.mov')):
            stream_urls.append(url)
        else:
            stream_urls = getStreamUrl(url)
        
        if not stream_urls:
            raise Exception('未解析到有效流地址')
        
        # 测试第一个流地址
        downloader = Downloader(stream_urls[0])
        downloadTester(downloader)
        speed = downloader.getSpeed()
        
        # 转换为MB/s
        speed_mb = speed / (1024 * 1024) if speed > 0 else -1
        
        resource['speed'] = speed_mb
        resource['delay'] = 0  # 可以添加延迟检测
        
    except Exception as e:
        resource['speed'] = -1
        resource['error_info'] = str(e)
    
    progress_dict['processed'] += 1
    processed = progress_dict['processed']
    total = progress_dict['total']
    if processed % 10 == 0:
        print(f"\r速度测试进度：{processed}/{total}", end='', flush=True)
    
    return resource

# 导入我们的检测模块
from resource_manager import ResourceManager
from utils.video_check import VideoChecker
from utils.url_check import URLChecker
from utils.config import config
from utils.tools import (
    get_pbar_remaining,
    format_interval
)
from utils.iptv_types import ChannelData, CategoryChannelData, ChannelItem
from iptv_checker import IPTVChecker


async def first():
    """主函数 - Step1-Step5"""
    checker = IPTVChecker()
    await checker.main()


if __name__ == "__main__":
    asyncio.run(first())
