#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 优化版本：解决内存和编码问题

import sys
import os
import re
import gc
import time
import threading
from datetime import datetime
import pytz
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import multiprocessing

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ======================== 全局配置模块 ========================
class Config:
    """全局配置类"""
    # 远程资源地址（限制数量以减少内存使用）
    REMOTE_URLS = [
        "https://gh-proxy.com/https://raw.githubusercontent.com/yoursmile66/TVBox/main/live.txt",
        "https://gh-proxy.com/https://github.moeyy.xyz/https://raw.githubusercontent.com/dxawi/0/main/tvlive.txt",
        "https://d.h6room.com/frjzb.txt"
    ]
    
    # 速度等级配置 (bytes/s) - 按从高到低排序
    SPEED_LEVELS = {
        'excellent': 1024 * 1024,  # 1MB/s
        'wonderful': 1024 * 700,   # 700KB/s
        'good': 1024 * 500,        # 500KB/s
        'useful': 1024 * 200       # 200KB/s
    }
    SPEED_LEVEL_ORDER = ['excellent', 'wonderful', 'good', 'useful']
    
    # 分类正则配置
    CATEGORY_PATTERNS = {
        '央视': re.compile(r'cctv|央视|中国中央电视台', re.I),
        '卫视': re.compile(r'卫视', re.I),
        '港澳台': re.compile(r'凤凰|无线|明珠|环球|美亚|翡翠|台视|中视|华视|中天|亚洲', re.I),
        '欧美': re.compile(r'al|ABC|BBC|Bloom|CBS|City|FOX|GB|go2|NBC|News|NTD|UN|Yah|trt', re.I),
        '其它': re.compile(r'4K|电影|四川|成都|上海|江苏|南京|新闻|高清|1080p', re.I)
    }
    
    # 画质正则配置
    QUALITY_PATTERNS = {
        '4K': re.compile(r'4k|4K|2160p', re.I),
        '超高清': re.compile(r'超高清|uhd|2160', re.I),
        '高清': re.compile(r'高清|hd|720p|1080p', re.I),
        'SD': re.compile(r'sd|480p|360p', re.I)
    }
    
    # 超时配置（减少超时时间以快速失败）
    TIMEOUT = {
        '404_check': 10,      # 404检测10秒超时
        'speed_test': 15,      # 速度测试15秒超时
        'remote_fetch': 30,    # 远程资源获取30秒超时
        'video_check': 180     # 视频检测3分钟超时
    }
    
    # 多进程配置（减少进程数以节省内存）
    MULTIPROCESS = {
        '404_processes': max(4, multiprocessing.cpu_count() // 2),  # 减少进程数
        'speed_processes': max(3, multiprocessing.cpu_count() // 3),   # 减少进程数
        'max_total_time': 1800
    }
    
    # 请求头
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 测速配置
    CHUNK_SIZE = 102400  # 100KB
    
    # 支持的视频流后缀
    VIDEO_SUFFIXES = ('.flv', '.mp4', '.ts', '.mkv', '.avi', '.mov')

# ======================== 数据模型模块 ========================
class StreamItem:
    """直播流数据模型"""
    def __init__(self, name, url):
        self.name = self._clean_text(name.strip())
        self.url = url.strip()
        self.speed = -1
        self.category = self._get_category()
        self.quality = self._get_quality()
        self.passed_404 = False
        self.speed_level = None
        self.test_duration = 0
        self.error_info = None
        self.is_whitelist = False  # 白名单标记
    
    def _clean_text(self, text):
        """清理文本，移除特殊字符"""
        if not text:
            return text
        # 移除可能导致编码问题的字符
        cleaned = re.sub(r'[^\x00-\x7F\u4e00-\u9FFF\u3000-\u303F\uFF00-\uFFEF]', '', text)
        return cleaned
    
    def _get_category(self):
        """获取分类"""
        for cat_name, pattern in Config.CATEGORY_PATTERNS.items():
            if pattern.search(self.name):
                return cat_name
        return None
    
    def _get_quality(self):
        """获取画质"""
        for q_name, pattern in Config.QUALITY_PATTERNS.items():
            if pattern.search(self.name):
                return q_name
        return 'SD'
    
    def _set_speed_level(self):
        """设置速度等级"""
        if self.speed <= 0:
            self.speed_level = None
            return
        
        # 白名单条目最低为useful等级
        if self.is_whitelist:
            for level in Config.SPEED_LEVEL_ORDER:
                if self.speed > Config.SPEED_LEVELS[level]:
                    self.speed_level = level
                    return
            # 如果速度低于所有等级阈值，白名单条目设为useful
            self.speed_level = 'useful'
            return
        
        # 普通条目按正常逻辑
        for level in Config.SPEED_LEVEL_ORDER:
            if self.speed > Config.SPEED_LEVELS[level]:
                self.speed_level = level
                return
        self.speed_level = None
    
    def __repr__(self):
        return f"<StreamItem {self.name} | {self.speed} bytes/s | 等级: {self.speed_level}>"

# ======================== 工具函数模块 ========================
def get_beijing_time(fmt='%Y%m%d%H%M'):
    """获取北京时间"""
    try:
        beijing_tz = pytz.timezone('Asia/Shanghai')
        return datetime.now(beijing_tz).strftime(fmt)
    except:
        return datetime.now().strftime(fmt)

def safe_decode(byte_data):
    """安全解码：优先utf-8，失败则用gbk，最后用ignore"""
    try:
        return byte_data.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return byte_data.decode('gbk')
        except UnicodeDecodeError:
            return byte_data.decode('utf-8', errors='ignore')

def check_ffmpeg():
    """检查FFmpeg是否可用"""
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

# ======================== 资源读取模块 ========================
def load_resources():
    """读取所有资源"""
    print("\n" + "="*80)
    print(f"【Step2: 读取资源】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    
    all_items = []
    # 读取白名单
    whitelist = _load_whitelist()
    # 读取本地M3U
    local_items = _load_local_m3u(whitelist)
    all_items.extend(local_items)
    print(f"本地M3U读取完成，共 {len(local_items)} 条")
    # 读取本地txt
    local_items = _load_local_txt(whitelist)
    all_items.extend(local_items)
    print(f"本地txt文件读取完成，共 {len(local_items)} 条")
    
    # 读取远程资源（限制数量）
    remote_items = _load_remote_resources(whitelist)
    all_items.extend(remote_items)
    print(f"远程资源读取完成，共 {len(remote_items)} 条")
    
    print(f"【Step2: 读取资源】总计读取 {len(all_items)} 条原始数据")
    
    # 强制垃圾回收
    gc.collect()
    
    return all_items

def _load_whitelist():
    """读取白名单文件"""
    whitelist = set()
    filename = "white.txt"
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 支持URL和名称匹配
                        whitelist.add(line)
            print(f"成功读取白名单 {filename}，共 {len(whitelist)} 条")
        except Exception as e:
            print(f"读取白名单文件 {filename} 失败: {e}")
    else:
        print(f"未找到白名单文件 {filename}，跳过白名单读取")
    return whitelist

def _load_local_m3u(whitelist):
    """读取本地M3U文件"""
    local_items = []
    filename = "resources.m3u"
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                extinf = ''
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('#EXTINF'):
                        extinf = line
                    elif extinf and not line.startswith('#'):
                        name = extinf.split(',')[-1].strip() if ',' in extinf else '未知'
                        item = StreamItem(name, line)
                        # 检查是否在白名单中
                        if name in whitelist or line in whitelist:
                            item.is_whitelist = True
                        local_items.append(item)
                        extinf = ''
            print(f"成功读取 {filename}")
        except Exception as e:
            print(f"读取本地文件 {filename} 失败: {e}")
    else:
        print(f"未找到 {filename} 文件，跳过M3U读取")
    return local_items

def _load_local_txt(whitelist):
    """读取本地TXT文件"""
    local_items = []
    filename = "resources.txt"
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if ',' in line and '^' not in line:
                        parts = line.split(',', 1)
                        if len(parts) == 2:
                            name = parts[0].strip() or '未知'
                            url = parts[1].strip()
                            if url:
                                item = StreamItem(name, url)
                                if name in whitelist or url in whitelist:
                                    item.is_whitelist = True
                                local_items.append(item)
                    elif '^' in line:
                        parts = line.split('^')
                        if len(parts) >= 2:
                            name = parts[0].strip() or '未知'
                            url = parts[1].strip()
                            if url:
                                item = StreamItem(name, url)
                                if name in whitelist or url in whitelist:
                                    item.is_whitelist = True
                                local_items.append(item)
            print(f"成功读取 {filename}")
        except Exception as e:
            print(f"读取本地文件 {filename} 失败: {e}")
    else:
        print(f"未找到 {filename} 文件，跳过TXT读取")
    return local_items

def _load_remote_resources(whitelist):
    """读取远程资源"""
    remote_items = []
    for url in Config.REMOTE_URLS:
        print(f"正在获取远程资源: {url}")
        try:
            req = Request(url, headers=Config.HEADERS)
            resp = urlopen(req, timeout=Config.TIMEOUT['remote_fetch'])
            
            if resp.getcode() == 404:
                print(f"资源不存在(404): {url}")
                continue
            
            content = resp.read().decode('utf-8', errors='ignore').splitlines()
            extinf = ''
            for line in content:
                line = line.strip()
                if not line or line.startswith('#EXTM3U') or line == '#genre#':
                    continue
                
                if ',' in line and not line.startswith('#'):
                    parts = line.split(',', 1)
                    if len(parts) == 2 and parts[1].strip():
                        name = parts[0]
                        stream_url = parts[1]
                        item = StreamItem(name, stream_url)
                        if name in whitelist or stream_url in whitelist:
                            item.is_whitelist = True
                        remote_items.append(item)
                elif line.startswith('#EXTINF'):
                    extinf = line
                elif extinf:
                    name = extinf.split(',')[-1].strip() if ',' in extinf else '未知'
                    item = StreamItem(name, line)
                    if name in whitelist or line in whitelist:
                        item.is_whitelist = True
                    remote_items.append(item)
                    extinf = ''
        except (HTTPError, URLError) as e:
            print(f"获取远程资源 {url} 失败: {e}")
        except Exception as e:
            print(f"处理远程资源 {url} 出错: {e}")
        
        # 强制垃圾回收
        gc.collect()
    
    return remote_items

# ======================== 主函数 ========================
def main():
    """主函数"""
    try:
        print("="*80)
        print(f"【直播流检测工具 - 优化版本】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # 初始化
        print("【Step1: 初始化】")
        if sys.platform == 'win32':
            multiprocessing.freeze_support()
        
        # 检查依赖
        try:
            import cv2
            import pymediainfo
            print("依赖检查通过")
        except ImportError as e:
            print(f"依赖检查失败: {e}")
            return
        
        # 读取资源
        items = load_resources()
        if not items:
            print("未找到任何资源，程序退出")
            return
        
        print(f"资源加载完成，共 {len(items)} 条")
        print("="*80)
        print(f"【检测完成】结束时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
    except Exception as e:
        print(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 强制垃圾回收
        gc.collect()

if __name__ == '__main__':
    main()
