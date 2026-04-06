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
            req = Request(m3u8, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=5) as resp:
                prefix = ''
                if '/' in m3u8:
                    prefix = m3u8[:m3u8.rindex('/') + 1]
                
                firstLine = True
                top = False
                second = False
                lines_processed = 0
                max_lines = 100
                for line in resp:
                    lines_processed += 1
                    if lines_processed > max_lines:
                        break
                    line = line.decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                    if firstLine:
                        if line != '#EXTM3U':
                            urls.append(m3u8)
                            break
                        firstLine = False
                        continue
                    if top:
                        if not line.lower().startswith('http'):
                            line = prefix + line
                        nested_urls = getStreamUrl(line, depth + 1)
                        urls.extend(nested_urls)
                        top = False
                    elif second:
                        if not line.lower().startswith('http'):
                            line = prefix + line
                        urls.append(line)
                        second = False
                    elif line.startswith('#EXT-X-STREAM-INF:'):
                        top = True
                    elif line.startswith('#EXTINF:'):
                        second = True
                urls = list(dict.fromkeys(urls))[:3]
        except Exception as e:
            pass
        return urls

    def downloadTester(downloader: Downloader):
        """下载测速"""
        try:
            req = Request(downloader.url, headers={'User-Agent': 'Mozilla/5.0'})
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
from utils.types import ChannelData, CategoryChannelData, ChannelItem


class IPTVChecker:
    """IPTV直播流检测器 - 基于IPTV API框架"""

    def __init__(self):
        self.update_progress = None
        self.run_ui = False
        self.tasks = []
        self.channel_items: CategoryChannelData = {}
        self.url_checker = URLChecker()
        self.video_checker = VideoChecker()
        self.pbar = None
        self.total = 0
        self.start_time = None
        
        # 设置环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['LANG'] = 'C.UTF-8'
        os.environ['LC_ALL'] = 'C.UTF-8'
        
        # 配置stdout编码
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    def pbar_update(self, name: str = ""):
        """更新进度条"""
        if self.pbar and self.pbar.n < self.total:
            self.pbar.update()
            remaining = get_pbar_remaining(n=self.pbar.n, total=self.total, start_time=self.start_time)
            self.update_progress(
                f"正在进行{name}, 剩余{self.total - self.pbar.n}个接口, 预计剩余时间: {remaining}",
                int((self.pbar.n / self.total) * 100),
            )

    def get_urls_len(self, is_filter: bool = False) -> int:
        """获取URL数量"""
        data = copy.deepcopy(self.channel_items)
        processed_urls = set(
            url_info["url"]
            for channel_obj in data.values()
            for url_info_list in channel_obj.values()
            for url_info in url_info_list
        )
        return len(processed_urls)

    def _format_duration(self, seconds: float) -> str:
        """格式化时间间隔"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}分{minutes}秒"
        elif minutes > 0:
            return f"{minutes}分{seconds}秒"
        else:
            return f"{seconds}秒"

    def _merge_channels(self, target: CategoryChannelData, source: CategoryChannelData):
        """合并频道数据"""
        for category, channels in source.items():
            if category not in target:
                target[category] = {}
            
            for channel_name, urls in channels.items():
                if channel_name not in target[category]:
                    target[category][channel_name] = []
                
                # 合并URL，避免重复
                existing_urls = {url_info.get('url') if isinstance(url_info, dict) else str(url_info) 
                               for url_info in target[category][channel_name]}
                
                for url_info in urls:
                    url = url_info.get('url') if isinstance(url_info, dict) else str(url_info)
                    if url and url not in existing_urls:
                        target[category][channel_name].append(url_info)

    async def main(self):
        """主处理函数 - 完成Step1~Step5的工作"""
        try:
            main_start_time = time_module.time()
            
            print("=" * 80)
            print(f"【IPTV直播流检测 - Step1~Step5】开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"基于IPTV API框架的稳定检测系统")
            print("=" * 80)
            
            # Step1: 读取所有资源
            print("\n📊 Step1: 读取所有资源（网上+本地）")
            print("-" * 50)
            
            # 初始化资源列表
            all_resources = []
            
            # 1.1 读取本地m3u资源
            local_m3u_count = 0
            if os.path.exists("resources.m3u"):
                print(f"� 解析resources.m3u...")
                m3u_resources = self._read_m3u_resources("resources.m3u")
                all_resources.extend(m3u_resources)
                local_m3u_count = len(m3u_resources)
                print(f"📖 解析resources.m3u: {local_m3u_count} 个资源")
            
            # 1.2 读取本地txt资源
            local_txt_count = 0
            if os.path.exists("resources.txt"):
                print(f"📖 解析resources.txt...")
                txt_resources = self._read_txt_resources("resources.txt")
                all_resources.extend(txt_resources)
                local_txt_count = len(txt_resources)
                print(f"📖 解析resources.txt: {local_txt_count} 个资源")
            
            # 1.3 读取远程资源
            remote_count = 0
            if os.path.exists("resources_remote.txt"):
                print(f"🌐 解析远程资源...")
                remote_resources = await self._read_remote_resources("resources_remote.txt")
                all_resources.extend(remote_resources)
                remote_count = len(remote_resources)
                print(f"🌐 解析远程资源: {remote_count} 个资源")
            
            # 1.4 读取白名单资源
            whitelist_count = 0
            if os.path.exists("white.txt"):
                print(f"📄 读取白名单资源...")
                whitelist_resources = self._read_whitelist_resources("white.txt")
                all_resources.extend(whitelist_resources)
                whitelist_count = len(whitelist_resources)
                print(f"📄 白名单资源: {whitelist_count} 个资源")
            
            print(f"📊 Step1详细统计:")
            print(f"   本地m3u资源: {local_m3u_count} 个")
            print(f"   本地txt资源: {local_txt_count} 个")
            print(f"   远程资源: {remote_count} 个")
            print(f"   白名单资源: {whitelist_count} 个")
            print(f"📊 Step1总资源: {len(all_resources)} 个")
            print(f"📋 资源来源构成:")
            print(f"   📁 本地文件: resources.m3u + resources.txt = {local_m3u_count + local_txt_count} 个")
            print(f"   🌐 网上资源: resources_remote.txt = {remote_count} 个")
            print(f"   ⚪ 白名单: white.txt = {whitelist_count} 个")
            
            # 显示Step1资源示例
            if all_resources:
                print(f"   Step1资源示例 (前5个):")
                for i, resource in enumerate(all_resources[:5]):
                    name = resource.get('name', '未知频道')
                    url = resource.get('url', '')
                    is_whitelist = resource.get('is_whitelist', False)
                    
                    info_parts = []
                    if is_whitelist:
                        info_parts.append("白名单")
                    
                    info_str = " | ".join(info_parts) if info_parts else "普通"
                    print(f"     {i+1}. {name} ({info_str})")
                    print(f"        URL: {url[:80]}{'...' if len(url) > 80 else ''}")
                
                if len(all_resources) > 5:
                    print(f"     ... 还有 {len(all_resources) - 5} 个资源")
            
            # 输出Step1接口文件
            self._save_step_output("step1_all_resources.txt", all_resources, "Step1: 所有原始资源")
            
            # Step2: URL去重，保留有name特征的url
            print("\n📊 Step2: URL去重处理")
            print("-" * 50)
            
            unique_resources = self._deduplicate_resources(all_resources)
            
            # 使用新的统计显示方法
            success_rate = (len(unique_resources)/len(all_resources)*100) if len(all_resources) > 0 else 0
            self._print_step_resources("Step2", all_resources, unique_resources, 
                                    f"去重成功率: {success_rate:.1f}%")
            
            # 输出Step2接口文件
            self._save_step_output("step2_unique_resources.txt", unique_resources, "Step2: 去重后资源")
            
            # Step4: 404筛查
            print("\n📊 Step4: 404筛查")
            print("-" * 50)
            
            valid_resources = await self._check_404_with_progress(unique_resources)
            
            # 使用新的统计显示方法
            if len(unique_resources) > 0:
                success_rate = (len(valid_resources)/len(unique_resources)*100) if len(unique_resources) > 0 else 0
                self._print_step_resources("Step4", unique_resources, valid_resources, 
                                        f"404筛查成功率: {success_rate:.1f}%")
                
                # 输出Step4接口文件
                self._save_step_output("step4_valid_resources.txt", valid_resources, "Step4: 404筛查后资源")
            else:
                print(f"📊 Step4完成:")
                print(f"   输入资源: 0")
                print(f"   输出资源: 0")
                print(f"   检测成功率: 0.0%")
            
            # Step5: 速度筛查（>200KB/s）
            print("\n📊 Step5: 速度筛查（>200KB/s）")
            print("-" * 50)
            
            speed_resources = await self._check_speed_with_progress(valid_resources)
            
            print(f"\n📊 Step5完成:")
            if len(valid_resources) > 0:
                # 使用新的统计显示方法
                success_rate = (len(speed_resources)/len(valid_resources)*100) if len(valid_resources) > 0 else 0
                self._print_step_resources("Step5", valid_resources, speed_resources, 
                                        f"速度筛查成功率: {success_rate:.1f}%")
                
                # 输出Step5接口文件
                self._save_step_output("step5_speed_resources.csv", speed_resources, "Step5: 速度筛查后资源")
                
                # 输出详细速度值
                print(f"\n📊 Step5速度详情:")
                print("-" * 80)
                print(f"{'频道名称':<30} {'速度(MB/s)':<15} {'速度(KB/s)':<15} {'延迟(ms)':<10}")
                print("-" * 80)
                
                # 按速度从高到低排序
                sorted_speed_resources = sorted(speed_resources, key=lambda x: x.get('speed', 0), reverse=True)
                
                for i, resource in enumerate(sorted_speed_resources[:20]):  # 显示前20个
                    name = resource.get('name', '未知频道')[:28]  # 截断长名称
                    speed_mb = resource.get('speed', 0)
                    speed_kb = speed_mb * 1024  # 转换为KB/s
                    delay = resource.get('delay', 'N/A')
                    
                    print(f"{name:<30} {speed_mb:<15.3f} {speed_kb:<15.1f} {delay:<10}")
                
                if len(sorted_speed_resources) > 20:
                    print(f"... 还有 {len(sorted_speed_resources) - 20} 个资源")
                
                print("-" * 80)
                print(f"速度范围: {sorted_speed_resources[-1].get('speed', 0):.3f} - {sorted_speed_resources[0].get('speed', 0):.3f} MB/s")
            else:
                print(f"   输入资源: 0")
                print(f"   输出资源: 0")
                print(f"   检测成功率: 0.0%")
                speed_resources = []  # 确保speed_resources存在
            
            # Step5完成 - 生成step5_speed_resources.csv文件
            print(f"\n🎉 Step1~Step5完成！")
            print(f"📄 已生成step5_speed_resources.csv文件，包含{len(speed_resources)}个资源")
            print(f"💡 请运行second.py继续Step6及以后的步骤")
            
            # 最终统计
            main_end_time = time_module.time()
            print(f"\n🎉 Step1~Step5检测完成！总耗时: {self._format_duration(main_end_time - main_start_time)}")
            print(f"📊 Step1~Step5统计: Step1={len(all_resources)}, Step2={len(unique_resources)}, Step4={len(valid_resources)}, Step5={len(speed_resources)}")
            if len(all_resources) > 0:
                print(f"📊 Step5转化率: {len(speed_resources)/len(all_resources)*100:.1f}% ({len(speed_resources)}/{len(all_resources)})")
            else:
                print(f"📊 Step5转化率: 0.0% (0/0)")
            
            return  # Step1~Step5完成，结束运行
            
        except Exception as e:
            print(f"❌ 主处理失败: {e}")
            import traceback
            traceback.print_exc()

    def _save_step_output(self, filename: str, resources: List[dict], description: str):
        """保存步骤输出文件到output目录"""
        try:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            filepath = output_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {description}\n")
                f.write(f"# 生成时间: {time_module.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 资源数量: {len(resources)}\n")
                
                # 统计白名单数量
                whitelist_count = sum(1 for r in resources if r.get('is_whitelist', False))
                if whitelist_count > 0:
                    f.write(f"# 白名单数量: {whitelist_count}\n")
                
                # 统计速度信息
                speed_resources = [r for r in resources if r.get('speed', 0) > 0]
                if speed_resources:
                    avg_speed = sum(r.get('speed', 0) for r in speed_resources) / len(speed_resources)
                    f.write(f"# 平均速度: {avg_speed:.3f} MB/s\n")
                
                f.write("#" * 50 + "\n\n")
                
                # 按名称排序输出
                sorted_resources = sorted(resources, key=lambda x: x.get('name', ''))
                
                for resource in sorted_resources:
                    name = resource.get('name', '未知频道')
                    url = resource.get('url', '')
                    speed = resource.get('speed', 0)
                    is_whitelist = resource.get('is_whitelist', False)
                    category = resource.get('category', '')
                    
                    # 构建输出行
                    info_parts = []
                    if is_whitelist:
                        info_parts.append("[白名单]")
                    if category:
                        info_parts.append(f"[{category}]")
                    if speed > 0:
                        info_parts.append(f"{speed:.3f}MB/s")
                    
                    info_str = " ".join(info_parts)
                    if info_str:
                        f.write(f"# {info_str}\n")
                    f.write(f"{name},{url}\n\n")
            
            print(f"📄 生成步骤文件: {filename} ({len(resources)} 个资源, 白名单: {whitelist_count})")
            
        except Exception as e:
            print(f"❌ 生成步骤文件失败: {filename} - {e}")

    def _print_step_resources(self, step_name: str, input_resources: List[dict], output_resources: List[dict], 
                           additional_info: str = ""):
        """打印步骤资源统计信息"""
        input_count = len(input_resources)
        output_count = len(output_resources)
        
        # 统计白名单
        input_whitelist = sum(1 for r in input_resources if r.get('is_whitelist', False))
        output_whitelist = sum(1 for r in output_resources if r.get('is_whitelist', False))
        
        # 统计速度信息
        input_speed = [r.get('speed', 0) for r in input_resources if r.get('speed', 0) > 0]
        output_speed = [r.get('speed', 0) for r in output_resources if r.get('speed', 0) > 0]
        
        print(f"\n📊 {step_name} 资源统计:")
        print(f"   输入资源: {input_count} 个 (白名单: {input_whitelist})")
        print(f"   输出资源: {output_count} 个 (白名单: {output_whitelist})")
        
        if input_speed:
            avg_input_speed = sum(input_speed) / len(input_speed)
            print(f"   输入平均速度: {avg_input_speed:.3f} MB/s")
        
        if output_speed:
            avg_output_speed = sum(output_speed) / len(output_speed)
            print(f"   输出平均速度: {avg_output_speed:.3f} MB/s")
        
        if additional_info:
            print(f"   {additional_info}")
        
        # 显示前几个资源的详细信息
        if output_resources:
            print(f"   输出资源示例 (前5个):")
            for i, resource in enumerate(output_resources[:5]):
                name = resource.get('name', '未知频道')
                url = resource.get('url', '')
                speed = resource.get('speed', 0)
                is_whitelist = resource.get('is_whitelist', False)
                category = resource.get('category', '')
                
                info_parts = []
                if is_whitelist:
                    info_parts.append("白名单")
                if category:
                    info_parts.append(f"{category}")
                if speed > 0:
                    info_parts.append(f"{speed:.3f}MB/s")
                
                info_str = " | ".join(info_parts)
                print(f"     {i+1}. {name} ({info_str})")
                print(f"        URL: {url[:80]}{'...' if len(url) > 80 else ''}")
            
            if len(output_resources) > 5:
                print(f"     ... 还有 {len(output_resources) - 5} 个资源")

    def _read_m3u_resources(self, file_path: str) -> List[dict]:
        """读取M3U文件资源"""
        resources = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            current_name = ""
            current_group = "默认分类"
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('#EXTINF:'):
                    # 解析频道信息
                    if 'group-title=' in line:
                        group_start = line.find('group-title="') + 13
                        group_end = line.find('"', group_start)
                        if group_end > group_start:
                            current_group = line[group_start:group_end]
                    
                    # 提取频道名称
                    if ',' in line:
                        name_start = line.rfind(',') + 1
                        current_name = line[name_start:].strip()
                
                elif line.startswith('#') or not line:
                    continue
                else:
                    # URL行
                    url = line
                    if current_name and url:
                        resources.append({
                            'url': url,
                            'name': current_name,
                            'category': current_group,
                            'source': 'm3u'
                        })
                        current_name = ""
        
        except Exception as e:
            print(f"❌ 读取M3U文件失败: {e}")
        
        return resources

    def _read_txt_resources(self, file_path: str) -> List[dict]:
        """读取TXT文件资源"""
        resources = []
        current_category = "默认分类"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 处理特殊格式：分组标题 ,#group#
                if ",#group#" in line:
                    # 提取分组名称
                    category_part = line.split(",#group#")[0].strip()
                    if category_part:
                        current_category = category_part
                    continue
                
                # 处理标准格式：#genre#分组名
                if "#genre#" in line:
                    parts = line.split(",")
                    if len(parts) >= 1:
                        genre_part = parts[0]
                        if "#genre#" in genre_part:
                            current_category = genre_part.replace("#genre#", "").strip()
                    continue
                
                # 解析频道名称和URL
                if "," in line:
                    parts = line.split(",", 1)
                    name = parts[0].strip()
                    url = parts[1].strip()
                    
                    if name and url and url.startswith('http'):
                        resources.append({
                            'url': url,
                            'name': name,
                            'category': current_category,
                            'source': 'txt'
                        })
        
        except Exception as e:
            print(f"❌ 读取TXT文件失败: {e}")
        
        return resources

    async def _read_remote_resources(self, file_path: str) -> List[dict]:
        """读取远程资源"""
        resources = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                remote_urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            
            for remote_url in remote_urls:
                try:
                    print(f"🌐 获取远程资源: {remote_url}")
                    resource_manager = ResourceManager()
                    remote_channels = await resource_manager._fetch_detailed_resources([remote_url])
                    
                    if remote_channels:
                        for category, channels in remote_channels.items():
                            for channel_name, urls in channels.items():
                                if isinstance(urls, list):
                                    for url in urls:
                                        url_str = url.get('url', '') if isinstance(url, dict) else str(url)
                                        if url_str:
                                            resources.append({
                                                'url': url_str,
                                                'name': channel_name,
                                                'category': category,
                                                'source': 'remote'
                                            })
                        print(f"✅ 远程资源获取成功: {remote_url}")
                    else:
                        print(f"❌ 远程资源为空: {remote_url}")
                except Exception as e:
                    print(f"❌ 远程资源获取失败: {remote_url} - {e}")
        
        except Exception as e:
            print(f"❌ 读取远程资源文件失败: {e}")
        
        return resources

    def _read_whitelist_resources(self, file_path: str) -> List[dict]:
        """读取白名单资源"""
        resources = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 支持两种格式：URL 或 名称,URL
                        if ',' in line:
                            parts = line.split(',', 1)
                            if len(parts) == 2:
                                name = parts[0].strip()
                                url = parts[1].strip()
                                if url:
                                    resources.append({
                                        'url': url,
                                        'name': name,
                                        'category': '白名单',
                                        'source': 'whitelist'
                                    })
                        else:
                            url = line
                            if url:
                                resources.append({
                                    'url': url,
                                    'name': '白名单资源',
                                    'category': '白名单',
                                    'source': 'whitelist'
                                })
        
        except Exception as e:
            print(f"❌ 读取白名单文件失败: {e}")
        
        return resources

    def _read_step5_csv_resources(self, file_path: str) -> List[dict]:
        """读取Step5 CSV文件资源"""
        resources = []
        lines = []
        
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                print(f"📋 使用编码 {encoding} 读取Step5 CSV文件成功")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"❌ 读取Step5 CSV文件失败: {e}")
                return resources
        
        if not lines:
            print("❌ 无法读取Step5 CSV文件")
            return resources
        
        current_category = "默认分类"
        current_speed = 0.0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 跳过文件头注释
            if line.startswith('#') and ('Step5' in line or '生成时间' in line or '资源数量' in line or '平均速度' in line or line.startswith('#' * 50)):
                continue
            
            # 解析分类和速度信息行，如：# [其它] 0.582MB/s
            if line.startswith('# [') and 'MB/s' in line:
                try:
                    # 提取分类信息
                    if ']' in line:
                        category_part = line[line.find('[') + 1:line.find(']')]
                        if category_part:
                            current_category = category_part.strip()
                    
                    # 提取速度信息
                    if 'MB/s' in line:
                        speed_part = line[line.find('MB/s') - 10:line.find('MB/s')]
                        speed_str = speed_part.strip().split()[-1]
                        try:
                            current_speed = float(speed_str)
                        except ValueError:
                            current_speed = 0.0
                except Exception:
                    pass
                continue
            
            # 解析资源行，格式：名称,URL
            if ',' in line and not line.startswith('#'):
                try:
                    parts = line.split(',', 1)
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        url = parts[1].strip()
                        
                        if name and url and url.startswith('http'):
                            resource = {
                                'name': name,
                                'url': url,
                                'category': current_category,
                                'speed': current_speed,
                                'is_whitelist': False
                            }
                            resources.append(resource)
                except Exception:
                    pass
        
        return resources

    def _deduplicate_resources(self, resources: List[dict]) -> List[dict]:
        """URL去重，保留有name特征的url"""
        unique_resources = {}
        
        for resource in resources:
            url = resource.get('url', '')
            name = resource.get('name', '')
            
            if not url:
                continue
                
            if url not in unique_resources:
                unique_resources[url] = resource
            else:
                # 如果URL重复，保留信息量最大的name
                existing = unique_resources[url]
                existing_name = existing.get('name', '')
                
                # 优先级：信息量大的优先
                existing_score = self._get_name_priority_score(existing_name)
                new_score = self._get_name_priority_score(name)
                
                if new_score > existing_score:
                    unique_resources[url] = resource
                elif new_score == existing_score:
                    # 如果信息量相同，保留较长的名称
                    if len(name) > len(existing_name):
                        unique_resources[url] = resource
        
        # 第二阶段：按name分组，保留所有不同的URL（为后续按速度排序做准备）
        name_groups = {}
        for url, resource in unique_resources.items():
            name = resource.get('name', '')
            if name not in name_groups:
                name_groups[name] = []
            name_groups[name].append(resource)
        
        # 展平所有资源（相同name的不同URL都会保留）
        final_resources = []
        for name, resources_list in name_groups.items():
            final_resources.extend(resources_list)
        
        return final_resources
    
    def _get_name_priority_score(self, name: str) -> int:
        """计算名称特征信息量分数"""
        if not name or name == '未知频道':
            return 1
        
        score = 1
        
        # 基础分数：名称长度
        score += min(len(name) // 3, 5)  # 每3个字符加1分，最多5分
        
        # 包含关键信息加分
        name_lower = name.lower()
        
        # 包含CCTV编号（如CCTV1、CCTV-1、CCTV 1等）
        if re.search(r'cctv\s*[-_]?\s*\d+', name_lower):
            score += 8
        
        # 包含卫视名称
        if '卫视' in name:
            score += 6
        
        # 包含知名媒体标识
        if any(keyword in name_lower for keyword in ['bbc', 'cnn', 'fox', 'nbc', 'abc', 'cbs']):
            score += 7
        
        # 包含分辨率信息
        if any(keyword in name_lower for keyword in ['4k', 'hd', '高清', '超清', 'uhd', '1080p']):
            score += 4
        
        # 包含地区信息
        if any(keyword in name for keyword in ['北京', '上海', '广东', '湖南', '江苏', '浙江']):
            score += 3
        
        # 包含频道类型信息
        if any(keyword in name_lower for keyword in ['新闻', '综合', '财经', '体育', '娱乐', '电影', '电视剧', 'news']):
            score += 3
        
        # 包含语言信息
        if any(keyword in name for keyword in ['中文', '英文', '粤语', '英语']):
            score += 2
        
        # 包含数字编号
        if re.search(r'\d+', name):
            score += 2
        
        return score

    def _read_source_file(self, file_path: str) -> CategoryChannelData:
        """读取源文件 - 支持M3U和TXT格式"""
        channels = {}
        current_category = "默认分类"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 检查文件格式
            if lines and lines[0].strip().startswith('#EXTM3U'):
                # M3U格式解析
                current_name = ""
                current_group = "默认分类"
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith('#EXTINF:'):
                        # 解析频道信息
                        if 'group-title=' in line:
                            # 提取分组
                            group_start = line.find('group-title="') + 13
                            group_end = line.find('"', group_start)
                            if group_end > group_start:
                                current_group = line[group_start:group_end]
                        
                        # 提取频道名称
                        if ',' in line:
                            name_start = line.rfind(',') + 1
                            current_name = line[name_start:].strip()
                    
                    elif line.startswith('#') or not line:
                        continue
                    else:
                        # URL行
                        url = line
                        if current_name and url:
                            if current_group not in channels:
                                channels[current_group] = {}
                            if current_name not in channels[current_group]:
                                channels[current_group][current_name] = []
                            channels[current_group][current_name].append({
                                'url': url,
                                'date': None,
                                'resolution': None,
                                'origin': 'source',
                                'ipv_type': None
                            })
                            current_name = ""
            
            elif lines and ',' in lines[0]:
                # TXT格式解析
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#') or ',' not in line:
                        continue
                    
                    if "#genre#" in line:
                        current_category = line.split(",")[0].replace("#genre#", "").strip()
                        if current_category not in channels:
                            channels[current_category] = {}
                    else:
                        # 解析频道名称和URL
                        if "," in line:
                            parts = line.split(",", 1)
                            name = parts[0].strip()
                            url = parts[1].strip()
                            
                            if name and url:
                                if name not in channels[current_category]:
                                    channels[current_category][name] = []
                                channels[current_category][name].append({
                                    'url': url,
                                    'date': None,
                                    'resolution': None,
                                    'origin': 'source',
                                    'ipv_type': None
                                })
        
        except Exception as e:
            print(f"❌ 读取源文件失败: {e}")
            return {}
        
        return channels

    async def _generate_results(self, results: List[Union[dict, object]], whitelist_results: List[Union[dict, object]] = None):
        """生成结果文件 - 使用whitelist_rules.txt筛查，白名单内容进入useful，其他按速度分级"""
        if whitelist_results is None:
            whitelist_results = []

        from pathlib import Path
        from datetime import datetime

        # Step7: 使用whitelist_rules.txt筛查名称和URL
        print("\n📊 Step7: 使用whitelist_rules.txt筛查名称和URL")
        print("-" * 50)
        
        filtered_results = self._filter_by_whitelist_rules(results)
        
        # 使用新的统计显示方法
        success_rate = (len(filtered_results)/len(results)*100) if len(results) > 0 else 0
        self._print_step_resources("Step7", results, filtered_results, 
                                f"whitelist筛查成功率: {success_rate:.1f}%")

        # 创建输出目录
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M")

        # 按速度阈值分级 (速度测试结果单位是MB/s，阈值需要转换为MB/s)
        speed_thresholds = {
            'excellent': 1024 * 1024 / (1024 * 1024),      # 1MB/s
            'wonderful': 1024 * 500 / (1024 * 1024),        # 500KB/s = 0.5MB/s
            'good': 1024 * 700 / (1024 * 1024),            # 700KB/s = 0.7MB/s
            'useful': 1024 * 200 / (1024 * 1024)           # 200KB/s = 0.2MB/s
        }

        # 生成useful文件：包含白名单内容 + 达到useful速度的非白名单内容
        useful_categories = {
            '欧美': [],
            '央视': [],
            '卫视': [],
            '港澳台': [],
            '其它': []
        }

        # 添加白名单内容到useful（确保完整包含）
        whitelist_urls = [item.get('url', '') for item in filtered_results if item.get('url')]
        whitelist_urls_set = set(whitelist_urls)
        
        # 从原始white.txt文件获取完整的白名单信息
        whitelist_channels = []
        if os.path.exists("white.txt"):
            with open("white.txt", 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            url = parts[1].strip()
                            if url and url.startswith('http'):
                                whitelist_channels.append((name, url))
        
        # 将白名单频道添加到useful分类中
        # 收集所有已添加的URL，避免重复
        added_urls = set()
        
        # 先添加白名单频道
        for name, url in whitelist_channels:
            category = self._classify_channel(name, url)
            # 只有分类不为None的白名单频道才添加
            if category is not None:
                useful_categories[category].append((name, url, 0))  # 白名单内容速度设为0
                added_urls.add(url)  # 记录已添加的URL
        
        print(f"📋 白名单频道添加: {len(whitelist_channels)} 个")

        # 添加达到useful速度的非白名单内容（useful是最低标准0.2MB/s，使用原始results）
        # 对于LU.txt，我们不跳过任何URL，因为它应该包含所有内容
        for item in results:  # 使用原始results而不是filtered_results
            if isinstance(item, dict):
                speed = item.get('speed', 0)
                name = item.get('name', '未知频道')
                url = item.get('url', '')
            else:
                speed = getattr(item, 'speed', 0)
                name = getattr(item, 'name', '未知频道')
                url = getattr(item, 'url', '')

            # 获取分类
            category = self._classify_channel(name, url)
            
            # 只有分类不为None的频道才添加（被排除的频道不添加）
            if category is None:
                continue
            
            # 跳过已经添加过的URL（避免与白名单重复）
            if url in added_urls:
                continue
            
            # LU.txt使用最低标准useful（0.2MB/s），不区分央视卫视
            min_speed = speed_thresholds['useful']  # 0.2MB/s
            
            # 速度单位已经是MB/s，直接比较
            if speed >= min_speed:
                useful_categories[category].append((name, url, speed))
                added_urls.add(url)  # 记录已添加的URL

        # 对每个分类进行排序
        for category in useful_categories:
            useful_categories[category] = self._sort_channels_by_priority(useful_categories[category], category)

        # 生成useful文件（TXT和CSV格式）
        # 生成TXT文件用于转换
        txt_filename = output_dir / f"LU.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            # 按欧美、央视、卫视、港澳台、其它顺序写入
            categories_order = ['欧美', '央视', '卫视', '港澳台', '其它']
            for category in categories_order:
                if useful_categories[category]:
                    f.write(f"{category},#group#\n")
                    f.write("\n")  # 在,#group#后增加一行空格
                    # 按质量和速度排序
                    sorted_channels = self._sort_channels_by_priority(useful_categories[category], category)
                    for name, url, speed in sorted_channels:
                        f.write(f"{name},{url}\n")
                    f.write("\n")  # 分类结束后添加空格

        # 生成CSV文件用于数据存储
        csv_filename = output_dir / f"LU.csv"
        with open(csv_filename, 'w', encoding='utf-8') as f:
            # 写入CSV头部
            f.write("名称,URL,分类,速度(MB/s)\n")
            
            # 按欧美、央视、卫视、港澳台、其它顺序写入
            categories_order = ['欧美', '央视', '卫视', '港澳台', '其它']
            for category in categories_order:
                if useful_categories[category]:
                    # 按质量和速度排序
                    sorted_channels = self._sort_channels_by_priority(useful_categories[category], category)
                    for name, url, speed in sorted_channels:
                        f.write(f"{name},{url},{category},{speed:.3f}\n")

        print(f"📄 生成文件: {txt_filename} (包含白名单内容 + 速度>={speed_thresholds['useful']*1024:.0f}KB/s的内容)")
        print(f"📄 生成文件: {csv_filename} (CSV格式数据)")

        # 生成excellent、wonderful、good文件（只包含非白名单内容）
        for quality in ['excellent', 'wonderful', 'good']:
            quality_categories = {
                '欧美': [],
                '央视': [],
                '卫视': [],
                '港澳台': [],
                '其它': []
            }

            threshold = speed_thresholds[quality]
            total_channels = 0

            # 只处理非白名单内容
            for item in filtered_results:
                if isinstance(item, dict):
                    speed = item.get('speed', 0)
                    name = item.get('name', '未知频道')
                    url = item.get('url', '')
                else:
                    speed = getattr(item, 'speed', 0)
                    name = getattr(item, 'name', '未知频道')
                    url = getattr(item, 'url', '')

                total_channels += 1

                # 获取分类
                category = self._classify_channel(name, url)
                
                # 只有分类不为None的频道才添加（被排除的频道不添加）
                if category is None:
                    continue
                
                # 对央视、卫视内容应用更严格的速度要求（1MB/s）
                if category in ['央视', '卫视']:
                    min_speed = speed_thresholds['excellent']  # 1MB/s
                else:
                    min_speed = threshold  # 使用该质量等级的正常阈值
                
                # 速度单位已经是MB/s，直接比较
                if speed >= min_speed:
                    quality_categories[category].append((name, url, speed))

            print(f"   {quality}: 总频道={total_channels}, 符合条件={sum(len(c) for c in quality_categories.values())}")

            # 对每个分类按质量和分辨率排序
            for category in quality_categories:
                quality_categories[category] = self._sort_channels_by_priority(quality_categories[category], category)

            # 生成该速度等级的文件（TXT和CSV格式）
            if quality == 'excellent':
                txt_filename = output_dir / f"LE.txt"
                csv_filename = output_dir / f"LE.csv"
            else:
                txt_filename = output_dir / f"live+{quality}+{timestamp}.txt"
                csv_filename = output_dir / f"live+{quality}+{timestamp}.csv"
            
            # 生成TXT文件用于转换
            with open(txt_filename, 'w', encoding='utf-8') as f:
                # 按欧美、央视、卫视、港澳台、其它顺序写入
                categories_order = ['欧美', '央视', '卫视', '港澳台', '其它']
                for category in categories_order:
                    if quality_categories[category]:
                        f.write(f"{category},#group#\n")
                        f.write("\n")  # 在,#group#后增加一行空格
                        # 按优先级排序：4D/超高清 > 高清/HD > SD，CCTV按数字升序，同速度降序
                        sorted_channels = self._sort_channels_by_priority(quality_categories[category], category)
                        for name, url, speed in sorted_channels:
                            f.write(f"{name},{url}\n")
                        f.write("\n")  # 分类结束后添加空格

            # 生成CSV文件用于数据存储
            with open(csv_filename, 'w', encoding='utf-8') as f:
                # 写入CSV头部
                f.write("名称,URL,分类,速度(MB/s)\n")
                
                # 按欧美、央视、卫视、港澳台、其它顺序写入
                categories_order = ['欧美', '央视', '卫视', '港澳台', '其它']
                for category in categories_order:
                    if quality_categories[category]:
                        # 按优先级排序：4D/超高清 > 高清/HD > SD，CCTV按数字升序，同速度降序
                        sorted_channels = self._sort_channels_by_priority(quality_categories[category], category)
                        for name, url, speed in sorted_channels:
                            f.write(f"{name},{url},{category},{speed:.3f}\n")

            speed_desc = f"速度 >= {threshold*1024:.0f}KB/s"
            print(f"📄 生成文件: {txt_filename} ({speed_desc}, 非白名单内容)")
            print(f"📄 生成文件: {csv_filename} (CSV格式数据)")

        print(f"📊 文件生成完成: useful(白名单+useful速度) + excellent/wonderful/good(按速度分级)")

    def _get_all_category_rules(self) -> dict:
        """从name_filtering_rules.txt获取所有分类的规则"""
        category_rules = {
            '欧美': [],
            '央视': [],
            '卫视': [],
            '港澳台': [],
            '其它': []
        }
        
        try:
            if os.path.exists("name_filtering_rules.txt"):
                with open("name_filtering_rules.txt", 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                current_category = None
                for line in lines:
                    line = line.strip()
                    
                    # 检查分类标题
                    if "☘️欧美,#genre#" in line:
                        current_category = "欧美"
                        continue
                    elif "📺央视,#genre#" in line:
                        current_category = "央视"
                        continue
                    elif "📡卫视,#genre#" in line:
                        current_category = "卫视"
                        continue
                    elif "🌊港·澳·台,#genre#" in line:
                        current_category = "港澳台"
                        continue
                    elif "🎬其它,#genre#" in line:
                        current_category = "其它"
                        continue
                    
                    # 收集规则
                    if current_category and line and not line.startswith('#'):
                        category_rules[current_category].append(line)
                        
        except Exception as e:
            print(f"❌ 读取name_filtering_rules.txt失败: {e}")
            
        return category_rules

    def _classify_channel(self, name: str, url: str) -> str:
        """分类频道 - 完全基于name_filtering_rules.txt"""
        name_lower = name.lower()
        
        # 获取所有分类规则
        all_rules = self._get_all_category_rules()
        
        # 按照分类顺序检查（欧美 -> 央视 -> 卫视 -> 港澳台 -> 其它）
        category_order = ['欧美', '央视', '卫视', '港澳台', '其它']
        
        for category in category_order:
            rules = all_rules[category]
            for rule in rules:
                if rule.lower() in name_lower:  # rule可在名称中任意位置
                    return category
        
        # 没有匹配任何规则的频道被排除
        return None  # 返回None表示不包含在任何分类中

    def _sort_channels_by_priority(self, channels: list, category: str = None) -> list:
        """按优先级排序频道：符合用户要求的5条规则，卫视类和欧美类特殊处理"""
        def get_quality_priority(name):
            """获取质量优先级：4D/超高清 > 高清/HD > SD"""
            name_lower = name.lower()
            
            # 4D或超高清
            if re.search(r'4d|超高清|uhd', name_lower, re.IGNORECASE):
                return 1
            # 高清或HD
            elif re.search(r'高清|hd|1080p', name_lower, re.IGNORECASE):
                return 2
            # SD
            else:
                return 3
        
        def get_cctv_number(name):
            """提取CCTV/CCTV数字，区分大小写，按数字升序"""
            # 优先匹配CCTV1, CCTV2等格式（区分大小写）
            match = re.search(r'CCTV(\d+)', name)
            if match:
                return int(match.group(1))
            # 再匹配cctv1, cctv2等格式（区分大小写）
            match = re.search(r'cctv(\d+)', name)
            if match:
                return int(match.group(1))
            # 匹配CCTV-1, CCTV-2等格式
            match = re.search(r'CCTV-(\d+)', name)
            if match:
                return int(match.group(1))
            # 匹配cctv-1, cctv-2等格式
            match = re.search(r'cctv-(\d+)', name)
            if match:
                return int(match.group(1))
            return 999  # 非CCTV频道返回大数字
        
        def get_pinyin_sort(name):
            """获取拼音排序（针对卫视类）"""
            if not name:
                return ""
            # 简单的拼音排序（可以根据需要扩展）
            return name.lower()
        
        def has_4k(name):
            """检查是否包含4K"""
            name_lower = name.lower()
            return bool(re.search(r'4k|4d|超高清|uhd', name_lower, re.IGNORECASE))
        
        def sort_key(channel):
            name, url, speed = channel
            
            # 卫视类特殊排序规则
            if category == '卫视':
                # 1. 4K频道和非4K频道完全分开
                is_4k = has_4k(name)
                # 2. 在各自分组内，名字按拼音顺序排列
                base_name = re.sub(r'[4kK]|超高清|UHD', '', name, flags=re.IGNORECASE).strip()
                pinyin_sort = get_pinyin_sort(base_name)
                # 3. 相同名字按速度降序排列
                return (not is_4k, pinyin_sort, -speed)  # not is_4k: False(4K)在前, True(非4K)在后
            
            # 欧美类和其它类按name_filtering_rules.txt中的规则顺序排序
            elif category in ['欧美', '其它']:
                all_rules = self._get_all_category_rules()
                category_rules = all_rules[category]
                
                for i, rule in enumerate(category_rules):
                    if rule.lower() in name.lower():
                        if category == '其它':
                            # 其它类：按rule顺序，同rule内按首字顺序
                            return (i, get_pinyin_sort(name), -speed)
                        else:
                            # 欧美类：按rule顺序，同rule内按速度降序
                            return (i, -speed)
                return (999, -speed)  # 没有匹配规则的放最后
            
            # 其他分类的排序规则（按用户要求）：
            # 1. 首先按质量分类：4D/超高清 > 高清/HD > SD
            # 2. 同质量内，CCTV/CCTV按数字升序（区分大小写）
            # 3. 同质量同类型，按名称首字排序
            # 4. 相同名称，按速度从大到小排序
            quality_priority = get_quality_priority(name)
            cctv_number = get_cctv_number(name)
            first_char_sort = get_pinyin_sort(name)
            
            return (quality_priority, cctv_number, first_char_sort, -speed)
        
        return sorted(channels, key=sort_key)

    def _sort_channels(self, channels: list) -> list:
        """按质量和分辨率排序频道"""
        def sort_key(channel):
            name, url, speed = channel
            name_lower = name.lower()
            url_lower = url.lower()
            
            # 4D或超高清
            if re.search(r'4d|超高清|uhd', name_lower, re.IGNORECASE):
                priority = 1
            # 高清或HD
            elif re.search(r'高清|hd|1080p', name_lower, re.IGNORECASE):
                priority = 2
            # SD
            else:
                priority = 3
            
            return (priority, -speed)  # 按优先级和速度排序
        
        return sorted(channels, key=sort_key)

    def update_progress(self, message: str, progress: int, complete: bool = False):
        """更新进度信息"""
        if complete:
            print(f"✅ {message}")
        else:
            print(f"🔄 {message} ({progress}%)")

    def _filter_by_whitelist_rules(self, results: List[Union[dict, object]]) -> List[Union[dict, object]]:
        """使用whitelist_rules.txt筛查资源名称和URL"""
        filtered_results = []
        
        # 加载白名单规则
        whitelist_rules = []
        current_category = ""
        
        if os.path.exists("whitelist_rules.txt"):
            try:
                # 尝试多种编码方式
                for encoding in ['utf-8', 'gbk', 'gb2312', 'big5']:
                    try:
                        with open("whitelist_rules.txt", 'r', encoding=encoding) as f:
                            content = f.read()
                            print(f"📋 使用编码 {encoding} 读取whitelist_rules.txt成功")
                            break
                    except UnicodeDecodeError:
                        continue
                else:
                    print("❌ 无法读取whitelist_rules.txt，尝试所有编码都失败")
                    return results
                
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 解析分类标题
                    if line.endswith(",#genre#"):
                        current_category = line.replace(",#genre#", "").strip()
                        continue
                    
                    # 添加规则到当前分类
                    if current_category:
                        whitelist_rules.append({
                            'rule': line,
                            'category': current_category
                        })
                        
            except Exception as e:
                print(f"❌ 读取whitelist_rules.txt失败: {e}")
                return results
        
        if not whitelist_rules:
            print("📋 无whitelist规则，保留所有资源")
            return results
        
        print(f"📋 加载whitelist规则: {len(whitelist_rules)} 条")
        
        # 统计各分类匹配数量
        category_stats = {}
        for rule_info in whitelist_rules:
            category = rule_info['category']
            if category not in category_stats:
                category_stats[category] = 0
        
        # 为了提高效率，先按分类分组规则
        rules_by_category = {}
        for rule_info in whitelist_rules:
            category = rule_info['category']
            if category not in rules_by_category:
                rules_by_category[category] = []
            rules_by_category[category].append(rule_info['rule'])
        
        for item in results:
            if isinstance(item, dict):
                name = item.get('name', '')
                url = item.get('url', '')
            else:
                name = getattr(item, 'name', '')
                url = getattr(item, 'url', '')
            
            if not name:
                continue
            
            # 检查是否匹配任何whitelist规则（不分大小写，不分位置）
            match_rule = False
            matched_category = ""
            
            for category, rules in rules_by_category.items():
                for rule in rules:
                    # 不区分大小写，不分位置的包含匹配
                    if rule.lower() in name.lower():
                        match_rule = True
                        matched_category = category
                        # 更新项目的分类
                        if isinstance(item, dict):
                            item['category'] = category
                        category_stats[category] += 1
                        break
                if match_rule:
                    break
            
            if match_rule:
                filtered_results.append(item)
        
        # 打印详细统计
        print(f"📋 whitelist规则匹配: {len(filtered_results)} 个资源")
        print("📋 各分类匹配统计:")
        for category, count in category_stats.items():
            if count > 0:
                print(f"   {category}: {count} 个")
        
        return filtered_results

    async def _check_404(self, resources: List[dict]) -> List[dict]:
        """404检测"""
        url_checker = URLChecker()
        
        # 提取URL列表
        urls_to_check = [resource['url'] for resource in resources]
        
        # 执行404检测
        print(f"🔍 开始404检测，共{len(urls_to_check)}个URL...")
        valid_results = await url_checker.check_urls_batch(urls_to_check)
        
        # 过滤有效结果并保留原始信息
        valid_resources = []
        for result in valid_results:
            url = result.get('url', '')
            # 找到对应的原始资源信息
            for resource in resources:
                if resource['url'] == url:
                    # 合并检测结果和原始信息
                    merged_resource = resource.copy()
                    merged_resource.update(result)
                    valid_resources.append(merged_resource)
                    break
        
        return valid_resources

    def _print_progress_bar(self, current: int, total: int, prefix: str = '', suffix: str = '', decimals: int = 1, length: int = 50, fill: str = '█'):
        """打印进度条"""
        percent = ("{0:." + str(decimals) + "f}").format(100 * (current / float(total)))
        filled_length = int(length * current // total)
        bar = fill * filled_length + '-' * (length - filled_length)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='', flush=True)
        if current == total:
            print()  # 完成时换行

    async def _check_404_with_progress(self, resources: List[dict]) -> List[dict]:
        """404检测（带进度条）"""
        url_checker = URLChecker()
        
        # 提取URL列表
        urls_to_check = [resource['url'] for resource in resources]
        
        print(f"开始404检测，共{len(urls_to_check)}个URL...")
        
        # 创建进度回调
        def progress_callback(current: int, total: int, valid: int):
            self._print_progress_bar(current, total, prefix='404检测', suffix=f'({valid}/{current} 有效)')
        
        # 执行404检测
        valid_results = await url_checker.check_urls_batch(urls_to_check, progress_callback)
        
        # 过滤有效结果并保留原始信息
        valid_resources = []
        for valid_url in valid_results:
            # 找到对应的原始资源信息
            for resource in resources:
                if resource['url'] == valid_url:
                    # 添加有效标记
                    merged_resource = resource.copy()
                    merged_resource['is_valid'] = True
                    valid_resources.append(merged_resource)
                    break
        
        return valid_resources

    async def _check_speed_with_progress(self, resources: List[dict]) -> List[dict]:
        """多进程速度检测（采用url-check_v-pro.py逻辑）"""
        
        # 提取URL列表
        urls_to_check = [resource['url'] for resource in resources]
        
        print(f"开始多进程速度检测，共{len(urls_to_check)}个URL...")
        # GitHub Actions环境使用更高的并发数
        if os.environ.get('GITHUB_ACTIONS'):
            # GitHub Actions: 2核CPU，但网络性能好，可以使用更多并发
            max_workers = 20
            print(f"GitHub Actions环境，使用并发数: {max_workers}")
        else:
            # 本地环境：根据CPU核心数调整
            max_workers = max(6, multiprocessing.cpu_count())
            print(f"本地环境，使用并发数: {max_workers}")
        
        total = len(resources)
        if total == 0:
            return []
        
        manager = multiprocessing.Manager()
        progress_dict = manager.dict()
        progress_dict['processed'] = 0
        progress_dict['total'] = total
        
        result = []
        try:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                worker_func = partial(test_speed_worker_global, progress_dict=progress_dict)
                for resource in resources:
                    futures.append(executor.submit(worker_func, resource))
                
                for future in futures:
                    try:
                        res = future.result(timeout=1800)
                        result.append(res)
                    except TimeoutError:
                        print(f"\n速度测试超时，强制终止")
                        executor.shutdown(wait=False, cancel_futures=True)
                        return []
                    except Exception as e:
                        print(f"\n单个速度测试任务出错: {e}")
                        continue
                        
        except Exception as e:
            print(f"\n速度检测进程池出错: {e}")
            return []
        
        # 过滤速度>200KB/s的结果 (200KB/s = 0.195MB/s)
        speed_threshold = 200 / 1024
        valid_speed_resources = []
        
        for resource in result:
            speed = resource.get('speed', 0)
            if speed >= speed_threshold:
                valid_speed_resources.append(resource)
        
        print(f"\n速度检测完成，有效资源: {len(valid_speed_resources)} 个")
        return valid_speed_resources

    async def _check_video_with_progress(self, resources: List[dict]) -> List[dict]:
        """画面变化与声音检测（采用video_check_worker.py逻辑）"""
        import subprocess
        import threading
        import json
        import asyncio
        import multiprocessing
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError, URLError
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def check_video_changes(url):
            """检测15秒内画面是否变化（调用video_check_worker.py）"""
            try:
                # 调用video_check_worker.py脚本
                result = subprocess.run([
                    'python', 'C:\\exe\\try\\video_check_worker.py', url
                ], capture_output=True, timeout=180)  # 3分钟超时
                
                if result.returncode == 0:
                    # 处理输出编码
                    try:
                        output = result.stdout.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            output = result.stdout.decode('gbk')
                        except UnicodeDecodeError:
                            output = result.stdout.decode('latin1', errors='ignore')
                    
                    # 查找JSON部分（从第一个{开始到最后一个}结束）
                    start_idx = output.find('{')
                    end_idx = output.rfind('}')
                    
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        json_str = output[start_idx:end_idx + 1]
                        video_result = json.loads(json_str)
                        return {
                            'has_video': video_result.get('success', False) and video_result.get('changing', False),
                            'has_audio': video_result.get('success', False),  # 如果检测成功认为有音频
                            'frame_info': video_result.get('frame_info', {}),
                            'reason': video_result.get('reason', ''),
                            'success': video_result.get('success', False)
                        }
                    else:
                        return {
                            'has_video': False,
                            'has_audio': False,
                            'reason': f'无法解析JSON输出: {output}',
                            'success': False
                        }
                else:
                    # 处理错误输出编码
                    try:
                        stderr = result.stderr.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            stderr = result.stderr.decode('gbk')
                        except UnicodeDecodeError:
                            stderr = result.stderr.decode('latin1', errors='ignore')
                    
                    return {
                        'has_video': False,
                        'has_audio': False,
                        'reason': f'脚本执行失败: {stderr}',
                        'success': False
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    'has_video': False,
                    'has_audio': False,
                    'reason': '画面检测超时（3分钟）',
                    'success': False
                }
            except Exception as e:
                return {
                    'has_video': False,
                    'has_audio': False,
                    'reason': f'检测异常: {str(e)}',
                    'success': False
                }

        # 提取URL列表
        urls_to_check = [resource['url'] for resource in resources]
        
        print(f"开始画面变化与声音检测，共{len(urls_to_check)}个URL...")
        
        # GitHub Actions环境使用更高的并发数
        if os.environ.get('GITHUB_ACTIONS'):
            # GitHub Actions: 2核CPU，但网络性能好，可以使用更多并发
            max_workers = 25
            print(f"GitHub Actions环境，使用并发数: {max_workers}")
        else:
            # 本地环境：根据CPU核心数调整
            cpu_count = multiprocessing.cpu_count()
            max_workers = min(
                cpu_count * 2,  # CPU核心数的2倍
                16,            # 最大不超过16个并发
                max(4, cpu_count)  # 最少4个并发
            )
            print(f"本地环境，CPU核心数: {cpu_count}，使用并发数: {max_workers}")
        
        # 创建进度跟踪
        processed_count = 0
        total = len(resources)
        valid_video_resources = []
        
        # 使用线程池进行并发处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_resource = {}
            for resource in resources:
                url = resource.get('url', '')
                future = executor.submit(check_video_changes, url)
                future_to_resource[future] = resource
            
            # 处理完成的任务
            for future in as_completed(future_to_resource):
                resource = future_to_resource[future]
                processed_count += 1
                
                # 更新进度
                if processed_count % 5 == 0:  # 每5个更新一次进度
                    self._print_progress_bar(processed_count, total, prefix='画面检测', suffix=f'({processed_count}/{total})')
                
                try:
                    # 获取检测结果
                    video_result = future.result()
                    
                    # 检查是否有画面变化或声音
                    has_video = video_result.get('has_video', False)
                    has_audio = video_result.get('has_audio', False)
                    success = video_result.get('success', False)
                    
                    if success and (has_video or has_audio):
                        # 合并视频检测结果和原始信息
                        merged_resource = resource.copy()
                        merged_resource.update(video_result)
                        valid_video_resources.append(merged_resource)
                        
                        # 输出调试信息（只显示前10个成功的）
                        if len(valid_video_resources) <= 10:
                            frame_info = video_result.get('frame_info', {})
                            print(f"✅ 画面检测成功 | URL: {resource.get('url', '')[:50]}... | 画面变化: {has_video} | 有声音: {has_audio}")
                    else:
                        # 打印失败原因（只显示前10个失败的）
                        reason = video_result.get('reason', '未知原因')
                        if processed_count <= 10:
                            print(f"❌ 画面检测失败 | URL: {resource.get('url', '')[:50]}... | 原因: {reason}")
                        
                except Exception as e:
                    print(f"❌ 处理检测结果异常: {e}")
                    continue
        
        # 完成进度条
        self._print_progress_bar(total, total, prefix='画面检测', suffix=f'({len(valid_video_resources)}/{total} 有效)')
        
        if not valid_video_resources:
            print("⚠️ 画面检测无有效结果，Step6输出为空")
            return []
        
        print(f"✅ 画面检测完成，有效资源: {len(valid_video_resources)} 个")
        return valid_video_resources

    async def _check_speed(self, resources: List[dict]) -> List[dict]:
        """速度检测，仅保留速度>200KB/s的资源"""
        url_checker = URLChecker()
        
        # 提取URL列表
        urls_to_check = [resource['url'] for resource in resources]
        
        # 执行速度检测
        print(f"⚡ 开始速度检测，共{len(urls_to_check)}个URL...")
        speed_results = await url_checker._test_speed_batch(urls_to_check)
        
        # 过滤速度>200KB/s的结果
        speed_threshold = 200 / 1024  # 200KB/s = 0.195MB/s
        valid_speed_resources = []
        
        for result in speed_results:
            speed = result.get('speed', 0)
            url = result.get('url', '')
            
            if speed >= speed_threshold:
                # 找到对应的原始资源信息
                for resource in resources:
                    if resource['url'] == url:
                        # 合并速度检测结果和原始信息
                        merged_resource = resource.copy()
                        merged_resource.update(result)
                        valid_speed_resources.append(merged_resource)
                        break
        
        return valid_speed_resources

    async def _check_video(self, resources: List[dict]) -> List[dict]:
        """视频检测（画面变化与声音）"""
        video_checker = VideoChecker()
        
        # 提取URL列表
        urls_to_check = [resource['url'] for resource in resources]
        
        print(f"🎬 开始视频检测，共{len(urls_to_check)}个URL...")
        
        # 执行视频检测
        video_results = await video_checker.check_videos_batch(urls_to_check)
        
        # 为视频检测结果添加原始信息
        valid_video_resources = []
        
        for video_result in video_results:
            url = video_result.get('url', '')
            has_video = video_result.get('has_video', False)
            has_audio = video_result.get('has_audio', False)
            
            # 检查是否有画面变化或声音
            if has_video or has_audio:
                # 找到对应的原始资源信息
                for resource in resources:
                    if resource['url'] == url:
                        # 合并视频检测结果和原始信息
                        merged_resource = resource.copy()
                        merged_resource.update(video_result)
                        valid_video_resources.append(merged_resource)
                        break
        
        # 如果视频检测结果为空，返回所有速度检测有效的资源
        if not valid_video_resources:
            print("⚠️ 视频检测无有效结果，返回所有速度检测有效的资源")
            return resources
        
        return valid_video_resources

    async def _run_conversion_tools(self):
        """运行转换工具"""
        import subprocess
        
        # 获取最新的文件
        from pathlib import Path
        output_dir = Path("output")
        utils_dir = Path(__file__).parent / "utils"
        
        # 只处理LE.txt和LU.txt文件
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
        if le_file.exists():
            print(f"🔄 转换 LE.txt -> LE.m3u")
            try:
                exe_path = utils_dir / "txt_to_m3u8b.exe"
                if exe_path.exists():
                    result = subprocess.run([str(exe_path), "LE.txt", "LE.m3u"], 
                                       cwd=output_dir, check=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"⚠️ exe转换失败，使用Python脚本")
                        # 直接使用Python脚本
                        subprocess.run([str(utils_dir / "txt_to_m3u8b.bat"), "LE.txt", "LE.m3u"], 
                                   cwd=output_dir, check=True)
                    else:
                        print(f"✅ 转换完成: LE.m3u")
                else:
                    # 使用Python脚本
                    subprocess.run([str(utils_dir / "txt_to_m3u8b.bat"), "LE.txt", "LE.m3u"], 
                               cwd=output_dir, check=True)
                    print(f"✅ 转换完成: LE.m3u")
            except subprocess.CalledProcessError as e:
                print(f"❌ 转换失败: {e}")
        
        if lu_file.exists():
            print(f"🔄 转换 LU.txt -> LU.m3u")
            try:
                exe_path = utils_dir / "txt_to_m3u8b.exe"
                if exe_path.exists():
                    result = subprocess.run([str(exe_path), "LU.txt", "LU.m3u"], 
                                       cwd=output_dir, check=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"⚠️ exe转换失败，使用Python脚本")
                        # 直接使用Python脚本
                        subprocess.run([str(utils_dir / "txt_to_m3u8b.bat"), "LU.txt", "LU.m3u"], 
                                   cwd=output_dir, check=True)
                    else:
                        print(f"✅ 转换完成: LU.m3u")
                else:
                    # 使用Python脚本
                    subprocess.run([str(utils_dir / "txt_to_m3u8b.bat"), "LU.txt", "LU.m3u"], 
                               cwd=output_dir, check=True)
                    print(f"✅ 转换完成: LU.m3u")
            except subprocess.CalledProcessError as e:
                print(f"❌ 转换失败: {e}")


async def main():
    """主函数"""
    checker = IPTVChecker()
    await checker.main()


if __name__ == "__main__":
    asyncio.run(main())
