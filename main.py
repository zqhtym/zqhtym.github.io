#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV直播流检测工具 - 基于IPTV API框架
Author: chaichunyang@outlook.com
"""

import asyncio
import copy
import os
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

# 导入我们的检测模块
from utils.video_check import VideoChecker
from utils.url_check import URLChecker
from utils.config import config
from utils.tools import (
    get_pbar_remaining,
    get_ip_address,
    convert_to_m3u,
    format_interval,
    resource_path,
    get_urls_from_file,
    get_version_info,
    update_file
)
from utils.types import ChannelData, CategoryChannelData


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
        data = copy.deepcopy(self.channel_data)
        processed_urls = set(
            url_info["url"]
            for channel_obj in data.values()
            for url_info_list in channel_obj.values()
            for url_info in url_info_list
        )
        return len(processed_urls)

    async def main(self):
        """主处理函数"""
        try:
            main_start_time = time()
            
            print("=" * 80)
            print(f"【IPTV直播流检测】开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"基于IPTV API框架的稳定检测系统")
            print("=" * 80)
            
            # Step1: 读取源文件
            source_file = config.source_file
            if not os.path.exists(source_file):
                print(f"❌ 源文件不存在: {source_file}")
                return
            
            print(f"📖 读取源文件: {source_file}")
            self.channel_items = self._read_source_file(source_file)
            
            if not self.channel_items:
                print("❌ 未找到频道数据")
                return
            
            # Step2: 提取所有URL
            all_urls = []
            for category, channels in self.channel_items.items():
                for channel_name, urls in channels.items():
                    for url_info in urls:
                        if isinstance(url_info, dict):
                            all_urls.append(url_info.get('url', ''))
                        else:
                            all_urls.append(str(url_info))
            
            all_urls = [url for url in all_urls if url and url.strip()]
            print(f"📊 提取到 {len(all_urls)} 个URL")
            
            if not all_urls:
                print("❌ 没有有效的URL需要检测")
                return
            
            # Step3: URL有效性检测
            print(f"\n🔍 开始URL有效性检测...")
            valid_urls = await self.url_checker.check_urls_batch(all_urls)
            print(f"✅ URL检测完成，有效: {len(valid_urls)} / {len(all_urls)}")
            
            if not valid_urls:
                print("❌ 没有有效的URL")
                return
            
            # Step4: 视频有效性检测
            print(f"\n🎬 开始视频有效性检测...")
            valid_video_urls = await self.video_checker.check_videos_batch(valid_urls)
            print(f"✅ 视频检测完成，有效: {len(valid_video_urls)} / {len(valid_urls)}")
            
            # Step5: 速度测试
            print(f"\n⚡ 开始速度测试...")
            speed_results = await self.url_checker.test_speed_batch(valid_video_urls)
            print(f"✅ 速度测试完成，有效: {len(speed_results)} / {len(valid_video_urls)}")
            
            # Step6: 生成结果
            print(f"\n📝 生成检测结果...")
            await self._generate_results(speed_results)
            
            total_time = format_interval(time() - main_start_time)
            print(f"\n🎉 检测完成！总耗时: {total_time}")
            print(f"📊 处理统计: 总URL={len(all_urls)}, 有效URL={len(valid_urls)}, 有效视频={len(valid_video_urls)}, 完成检测={len(speed_results)}")
            
        except Exception as e:
            print(f"❌ 检测过程中出错: {e}")
            import traceback
            traceback.print_exc()

    def _read_source_file(self, file_path: str) -> CategoryChannelData:
        """读取源文件"""
        channels = {}
        current_category = "默认分类"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
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
        
        return channels

    async def _generate_results(self, results: list):
        """生成检测结果"""
        if not results:
            print("❌ 没有结果需要生成")
            return
        
        # 按速度分组
        excellent = []  # > 1MB/s
        wonderful = []  # > 700KB/s  
        good = []       # > 500KB/s
        useful = []     # > 200KB/s
        
        for item in results:
            speed = getattr(item, 'speed', 0)
            name = getattr(item, 'name', '未知频道')
            url = getattr(item, 'url', '')
            
            if speed > 1024 * 1024:
                excellent.append(f"{name},{url}")
            elif speed > 1024 * 700:
                wonderful.append(f"{name},{url}")
            elif speed > 1024 * 500:
                good.append(f"{name},{url}")
            elif speed > 1024 * 200:
                useful.append(f"{name},{url}")
        
        # 创建输出目录
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 生成分类文件
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        
        for category, urls, quality in [
            ("央视", excellent, "excellent"),
            ("卫视", wonderful, "wonderful"), 
            ("港澳台", good, "good"),
            ("其它", useful, "useful")
        ]:
            if urls:
                filename = output_dir / f"live+{quality}+{timestamp}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"#genre#{category}\n")
                    for url_line in urls:
                        f.write(f"{url_line}\n")
                print(f"📄 生成文件: {filename} ({len(urls)}个)")

    def update_progress(self, message: str, progress: int, complete: bool = False):
        """更新进度信息"""
        if complete:
            print(f"✅ {message}")
        else:
            print(f"🔄 {message} ({progress}%)")


async def main():
    """主函数"""
    checker = IPTVChecker()
    await checker.main()


if __name__ == "__main__":
    asyncio.run(main())
