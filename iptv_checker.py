#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV检测器核心模块 - 独立模块
提供 IPTVChecker 类供 main.py、second.py、third.py 使用
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

    async def _generate_results(self, video_resources: List[dict]):
        """生成最终结果文件"""
        import subprocess
        
        # 创建输出目录
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 按速度分类
        excellent_resources = []  # >= 2MB/s
        wonderful_resources = []  # >= 1MB/s  
        good_resources = []      # >= 0.7MB/s
        useful_resources = []     # >= 0.5MB/s
        
        for resource in video_resources:
            speed = resource.get('speed', 0)
            if speed >= 2.0:
                excellent_resources.append(resource)
            elif speed >= 1.0:
                wonderful_resources.append(resource)
            elif speed >= 0.7:
                good_resources.append(resource)
            elif speed >= 0.5:
                useful_resources.append(resource)
        
        # 生成不同级别的文件
        current_time = datetime.now().strftime('%Y%m%d%H%M')
        
        # 生成 useful 级别文件 (>= 0.5MB/s)
        if useful_resources:
            useful_file = output_dir / f"live+useful+{current_time}.txt"
            useful_csv = output_dir / f"live+useful+{current_time}.csv"
            
            with open(useful_file, 'w', encoding='utf-8') as f:
                for resource in useful_resources:
                    f.write(f"{resource['name']},{resource['url']}\n")
            
            with open(useful_csv, 'w', encoding='utf-8') as f:
                f.write("名称,URL,速度(MB/s),分类\n")
                for resource in useful_resources:
                    f.write(f"{resource['name']},{resource['url']},{resource.get('speed', 0):.3f},{resource.get('category', '')}\n")
            
            print(f"📄 生成文件: {useful_file} (速度 >= 500KB/s, 非白名单内容)")
            print(f"📄 生成文件: {useful_csv} (CSV格式数据)")
        
        # 生成 good 级别文件 (>= 0.7MB/s)
        if good_resources:
            good_file = output_dir / f"live+good+{current_time}.txt"
            good_csv = output_dir / f"live+good+{current_time}.csv"
            
            with open(good_file, 'w', encoding='utf-8') as f:
                for resource in good_resources:
                    f.write(f"{resource['name']},{resource['url']}\n")
            
            with open(good_csv, 'w', encoding='utf-8') as f:
                f.write("名称,URL,速度(MB/s),分类\n")
                for resource in good_resources:
                    f.write(f"{resource['name']},{resource['url']},{resource.get('speed', 0):.3f},{resource.get('category', '')}\n")
            
            print(f"📄 生成文件: {good_file} (速度 >= 700KB/s, 非白名单内容)")
            print(f"📄 生成文件: {good_csv} (CSV格式数据)")
        
        # 生成 wonderful 级别文件 (>= 1MB/s)
        if wonderful_resources:
            wonderful_file = output_dir / f"live+wonderful+{current_time}.txt"
            wonderful_csv = output_dir / f"live+wonderful+{current_time}.csv"
            
            with open(wonderful_file, 'w', encoding='utf-8') as f:
                for resource in wonderful_resources:
                    f.write(f"{resource['name']},{resource['url']}\n")
            
            with open(wonderful_csv, 'w', encoding='utf-8') as f:
                f.write("名称,URL,速度(MB/s),分类\n")
                for resource in wonderful_resources:
                    f.write(f"{resource['name']},{resource['url']},{resource.get('speed', 0):.3f},{resource.get('category', '')}\n")
            
            print(f"📄 生成文件: {wonderful_file} (速度 >= 500KB/s, 非白名单内容)")
            print(f"📄 生成文件: {wonderful_csv} (CSV格式数据)")
        
        # 生成 excellent 级别文件 (>= 2MB/s)
        if excellent_resources:
            excellent_file = output_dir / f"live+excellent+{current_time}.txt"
            excellent_csv = output_dir / f"live+excellent+{current_time}.csv"
            
            with open(excellent_file, 'w', encoding='utf-8') as f:
                for resource in excellent_resources:
                    f.write(f"{resource['name']},{resource['url']}\n")
            
            with open(excellent_csv, 'w', encoding='utf-8') as f:
                f.write("名称,URL,速度(MB/s),分类\n")
                for resource in excellent_resources:
                    f.write(f"{resource['name']},{resource['url']},{resource.get('speed', 0):.3f},{resource.get('category', '')}\n")
            
            print(f"📄 生成文件: {excellent_file} (速度 >= 2MB/s, 非白名单内容)")
            print(f"📄 生成文件: {excellent_csv} (CSV格式数据)")
        
        # 生成 LE.txt 和 LU.txt (兼容原有格式)
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
        # LE.txt: 包含所有级别的资源
        all_resources = useful_resources + good_resources + wonderful_resources + excellent_resources
        with open(le_file, 'w', encoding='utf-8') as f:
            for resource in all_resources:
                f.write(f"{resource['name']},{resource['url']}\n")
        
        # LU.txt: 只包含 good 及以上级别的资源
        lu_resources = good_resources + wonderful_resources + excellent_resources
        with open(lu_file, 'w', encoding='utf-8') as f:
            for resource in lu_resources:
                f.write(f"{resource['name']},{resource['url']}\n")
        
        # 统计信息
        total_channels = len(set(r['name'] for r in video_resources))
        good_channels = len(set(r['name'] for r in lu_resources))
        
        print(f"   good: 总频道={total_channels}, 符合条件={good_channels}")
        print(f"📊 文件生成完成: useful(白名单+useful速度) + excellent/wonderful/good(按速度分级)")

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
                # 优先使用exe文件
                exe_path = utils_dir / "txt_to_m3u8b.exe"
                bat_path = utils_dir / "txt_to_m3u8b.bat"
                py_path = utils_dir / "txt_to_m3u8b.py"
                
                # 首先尝试exe文件
                if exe_path.exists():
                    try:
                        result = subprocess.run([str(exe_path), "LE.txt", "LE.m3u"], 
                                             cwd=output_dir, check=True, capture_output=True, text=True)
                        print(f"✅ 转换完成: LE.m3u (Exe文件)")
                    except (subprocess.CalledProcessError, PermissionError, FileNotFoundError) as e:
                        print(f"⚠️ exe转换失败: {str(e)}，尝试Python脚本")
                        # exe失败，尝试Python脚本
                        if py_path.exists():
                            try:
                                subprocess.run(["python", str(py_path), "LE.txt", "LE.m3u"], 
                                             cwd=output_dir, check=True, capture_output=True, text=True)
                                print(f"✅ 转换完成: LE.m3u (Python脚本)")
                            except (subprocess.CalledProcessError, FileNotFoundError):
                                # Python脚本失败，尝试bat脚本
                                if bat_path.exists():
                                    subprocess.run([str(bat_path), "LE.txt", "LE.m3u"], 
                                                 cwd=output_dir, check=True)
                                    print(f"✅ 转换完成: LE.m3u (Bat脚本)")
                                else:
                                    print(f"❌ 所有转换工具都失败")
                        else:
                            print(f"❌ 找不到Python转换脚本")
                else:
                    print(f"❌ 找不到exe文件: txt_to_m3u8b.exe")
                    
            except Exception as e:
                print(f"❌ 转换异常: {e}")
        
        if lu_file.exists():
            print(f"🔄 转换 LU.txt -> LU.m3u")
            try:
                # 优先使用exe文件
                exe_path = utils_dir / "txt_to_m3u8b.exe"
                bat_path = utils_dir / "txt_to_m3u8b.bat"
                py_path = utils_dir / "txt_to_m3u8b.py"
                
                # 首先尝试exe文件
                if exe_path.exists():
                    try:
                        result = subprocess.run([str(exe_path), "LU.txt", "LU.m3u"], 
                                             cwd=output_dir, check=True, capture_output=True, text=True)
                        print(f"✅ 转换完成: LU.m3u (Exe文件)")
                    except (subprocess.CalledProcessError, PermissionError, FileNotFoundError) as e:
                        print(f"⚠️ exe转换失败: {str(e)}，尝试Python脚本")
                        # exe失败，尝试Python脚本
                        if py_path.exists():
                            try:
                                subprocess.run(["python", str(py_path), "LU.txt", "LU.m3u"], 
                                             cwd=output_dir, check=True, capture_output=True, text=True)
                                print(f"✅ 转换完成: LU.m3u (Python脚本)")
                            except (subprocess.CalledProcessError, FileNotFoundError):
                                # Python脚本失败，尝试bat脚本
                                if bat_path.exists():
                                    subprocess.run([str(bat_path), "LU.txt", "LU.m3u"], 
                                                 cwd=output_dir, check=True)
                                    print(f"✅ 转换完成: LU.m3u (Bat脚本)")
                                else:
                                    print(f"❌ 所有转换工具都失败")
                        else:
                            print(f"❌ 找不到Python转换脚本")
                else:
                    print(f"❌ 找不到exe文件: txt_to_m3u8b.exe")
                    
            except Exception as e:
                print(f"❌ 转换异常: {e}")

    def _read_step6_csv_resources(self, file_path: str) -> list:
        """读取Step6 CSV文件资源"""
        resources = []
        lines = []
        
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                print(f"📋 使用编码 {encoding} 读取Step6 CSV文件成功")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"❌ 读取Step6 CSV文件失败: {e}")
                return resources
        
        if not lines:
            print("❌ 无法读取Step6 CSV文件")
            return resources
        
        current_category = "默认分类"
        current_speed = 0.0
        has_video = False
        has_audio = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 跳过文件头注释
            if line.startswith('#') and ('Step6' in line or '生成时间' in line or '资源数量' in line or '平均速度' in line or line.startswith('#' * 50)):
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
                                'has_video': has_video,
                                'has_audio': has_audio,
                                'is_whitelist': False
                            }
                            resources.append(resource)
                except Exception:
                    pass
        
        return resources

    def _read_step5_csv_resources(self, file_path: str) -> list:
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

    def _save_step_output(self, filename: str, resources: List[dict], description: str):
        """保存步骤输出文件"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入文件头
            f.write(f"# {description}\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 资源数量: {len(resources)}\n")
            
            if resources:
                # 计算平均速度
                speeds = [r.get('speed', 0) for r in resources if r.get('speed', 0) > 0]
                avg_speed = sum(speeds) / len(speeds) if speeds else 0
                f.write(f"# 平均速度: {avg_speed:.3f} MB/s\n")
            
            f.write("#" * 50 + "\n\n")
            
            # 按分类分组
            categories = {}
            for resource in resources:
                category = resource.get('category', '默认分类')
                if category not in categories:
                    categories[category] = []
                categories[category].append(resource)
            
            # 写入各分类资源
            for category, category_resources in categories.items():
                # 计算分类平均速度
                speeds = [r.get('speed', 0) for r in category_resources if r.get('speed', 0) > 0]
                avg_speed = sum(speeds) / len(speeds) if speeds else 0
                
                f.write(f"# [{category}] {avg_speed:.3f}MB/s\n")
                for resource in category_resources:
                    f.write(f"{resource['name']},{resource['url']}\n")
                f.write("\n")
        
        print(f"📄 已生成: {output_file}")

    def _print_step_resources(self, step_name: str, input_resources: List[dict], 
                           output_resources: List[dict], description: str):
        """打印步骤资源统计"""
        print(f"📊 {step_name}完成:")
        print(f"   输入资源: {len(input_resources)}")
        print(f"   输出资源: {len(output_resources)}")
        print(f"   {description}")
        
        if output_resources:
            # 按分类统计
            categories = {}
            for resource in output_resources:
                category = resource.get('category', '默认分类')
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1
            
            print(f"📋 分类统计:")
            for category, count in sorted(categories.items()):
                print(f"   {category}: {count} 个")

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
                script_path = 'utils/video_check_worker.py'
                # 使用环境变量配置的超时时间
                timeout = int(os.environ.get('VIDEO_TOTAL_TIMEOUT', 180))
                result = subprocess.run([
                    'python', script_path, url
                ], capture_output=True, timeout=timeout)
                
                if result.returncode == 0:
                    # 处理输出编码
                    try:
                        output = result.stdout.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            output = result.stdout.decode('gbk')
                        except UnicodeDecodeError:
                            output = result.stdout.decode('latin1', errors='ignore')

                    # 找到JSON部分（从第一个{到最后一个}）
                    start_idx = output.find('{')
                    end_idx = output.rfind('}')

                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        json_str = output[start_idx:end_idx + 1]
                        video_result = json.loads(json_str)
                        return {
                            'has_video': video_result.get('has_video', False),
                            'has_audio': video_result.get('has_audio', False),
                            'video_changing': video_result.get('video_changing', False) or video_result.get('changing', False),
                            'frame_info': video_result.get('frame_info', {}),
                            'reason': video_result.get('reason', '') or video_result.get('error', ''),
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
                    
                    # 处理空的stderr
                    stderr_msg = stderr.strip() if stderr else '未知错误'
                    return {
                        'has_video': False,
                        'has_audio': False,
                        'reason': f'脚本执行失败: {stderr_msg}',
                        'success': False
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    'has_video': False,
                    'has_audio': False,
                    'reason': f'画面检测超时（{timeout}秒）',
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
        
        # GitHub Actions环境使用优化的并发数（考虑网络限制）
        if os.environ.get('GITHUB_ACTIONS'):
            # GitHub Actions: 严格限制并发数以避免网络限制
            max_workers = int(os.environ.get('GITHUB_ACTIONS_WORKERS', 3))  # 降低到3个并发
            print(f"GitHub Actions环境，使用保守并发数: {max_workers} (避免网络限制)")
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
        
        # GitHub Actions环境下分批处理以避免网络限制
        if os.environ.get('GITHUB_ACTIONS'):
            # 分批处理：每批50个资源，避免网络限制
            batch_size = 50
            valid_video_resources = []
            total_batches = (len(resources) + batch_size - 1) // batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(resources))
                batch_resources = resources[start_idx:end_idx]
                
                print(f"🔄 处理第{batch_idx + 1}/{total_batches}批 (资源: {len(batch_resources)}个)", flush=True)
                
                # 使用线程池处理当前批次
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_resource = {}
                    for resource in batch_resources:
                        url = resource.get('url', '')
                        future = executor.submit(check_video_changes, url)
                        future_to_resource[future] = resource
                    
                    # 处理当前批次的任务
                    batch_valid_count = 0
                    for future in as_completed(future_to_resource):
                        resource = future_to_resource[future]
                        processed_count += 1
                        
                        try:
                            video_result = future.result()
                            has_video = video_result.get('has_video', False)
                            has_audio = video_result.get('has_audio', False)
                            success = video_result.get('success', False)
                            video_changing = video_result.get('video_changing', False)
                            
                            if success and (has_video or has_audio):
                                # 合并视频检测结果和原始信息
                                merged_resource = resource.copy()
                                merged_resource.update(video_result)
                                valid_video_resources.append(merged_resource)
                                batch_valid_count += 1
                                
                                # 实时显示成功资源
                                name = resource.get('name', '未知频道')[:30]
                                print(f"✅ [{processed_count}/{len(resources)}] {name}", flush=True)
                            else:
                                # 记录失败原因
                                reason = video_result.get('reason', '') or video_result.get('error', '')
                                name = resource.get('name', '未知频道')[:30]
                                print(f"❌ [{processed_count}/{len(resources)}] {name} - {reason[:40]}", flush=True)
                                
                                # GitHub Actions环境下的网络问题诊断
                                if os.environ.get('GITHUB_ACTIONS'):
                                    if '404' in reason:
                                        print(f"🔍 GitHub Actions诊断: URL失效 (404错误)")
                                    elif 'timeout' in reason.lower():
                                        print(f"🔍 GitHub Actions诊断: 网络超时 (可能被限制)")
                                    elif 'connection' in reason.lower():
                                        print(f"🔍 GitHub Actions诊断: 连接失败 (网络限制)")
                                    elif '无法打开视频流' in reason:
                                        print(f"🔍 GitHub Actions诊断: 流媒体访问被阻 (可能IP被限制)")
                                    else:
                                        print(f"🔍 GitHub Actions诊断: 其他错误 - {reason}")
                        except Exception as e:
                            print(f"❌ 处理检测结果异常: {e}")
                            continue
                
                print(f"✅ 第{batch_idx + 1}批完成，有效资源: {batch_valid_count}个", flush=True)
                
                # 批次间暂停，避免网络限制
                if batch_idx < total_batches - 1:
                    print(f"⏱️ 批次间暂停2秒，避免网络限制...", flush=True)
                    import time
                    time.sleep(2)
        else:
            # 本地环境：一次性处理所有资源
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
                    has_video = video_result.get('has_video', False)
                    has_audio = video_result.get('has_audio', False)
                    success = video_result.get('success', False)
                    video_changing = video_result.get('video_changing', False)
                    
                    if success and (has_video or has_audio):
                        # 合并视频检测结果和原始信息
                        merged_resource = resource.copy()
                        merged_resource.update(video_result)
                        valid_video_resources.append(merged_resource)
                        
                        # 显示成功信息
                        name = resource.get('name', '未知频道')[:30]
                        print(f"✅ [{processed_count}/{total}] {name} - 画面变化: {video_changing}, 有声音: {has_audio}")
                    else:
                        # 记录失败原因
                        reason = video_result.get('reason', '') or video_result.get('error', '')
                        name = resource.get('name', '未知频道')[:30]
                        print(f"❌ [{processed_count}/{total}] {name} - {reason[:40]}")
                        
                except Exception as e:
                    print(f"❌ 处理检测结果异常: {e}")
                    continue
        
        print(f"\n✅ 画面检测完成，有效资源: {len(valid_video_resources)} 个")
        return valid_video_resources

    def _print_progress_bar(self, current: int, total: int, prefix: str = '', suffix: str = '', decimals: int = 1, length: int = 50, fill: str = '█'):
        """打印进度条"""
        percent = ("{0:." + str(decimals) + "f}").format(100 * (current / float(total)))
        filled_length = int(length * current // total)
        bar = fill * filled_length + '-' * (length - filled_length)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='', flush=True)
        if current == total:
            print()  # 完成时换行
