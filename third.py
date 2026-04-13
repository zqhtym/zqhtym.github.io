#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

"""
IPTV检测工具 - Step1及Step7以后步骤
支持单独运行Step1或从Step7开始运行
"""

import asyncio
import csv
import os
import time
from pathlib import Path
from typing import Dict, List
import aiohttp
from datetime import datetime
import re

# 导入独立模块
from iptv_checker import IPTVChecker

class ThirdChecker(IPTVChecker):
    """Step1 and Step7+"""
    
    def __init__(self):
        super().__init__()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    async def run_step1_only(self):
        """Step1: IPTV"""
        try:
            print("=" * 80)
            print(f" IPTV  - Step1 : {self._get_current_time()}")
            print("=" * 80)
            
            print("\n[Step1] IPTV...")
            
            # 
            all_resources = {}
            
            # 1.  resources.m3u 
            print("[INFO]  resources.m3u ...")
            m3u_resources = await self._load_m3u_file("resources.m3u")
            if m3u_resources:
                all_resources.update(m3u_resources)
                print(f"[SUCCESS] resources.m3u ,  {len(m3u_resources)} ")
            
            # 2.  resources.txt 
            print("[INFO]  resources.txt ...")
            txt_resources = await self._load_txt_file("resources.txt")
            if txt_resources:
                all_resources.update(txt_resources)
                print(f"[SUCCESS] resources.txt ,  {len(txt_resources)} ")
            
            # 3.  URL 
            print("[INFO]  URL ...")
            remote_urls = [
                #  URL
            ]
            
            remote_count = 0
            for remote_url in remote_urls:
                try:
                    print(f"[INFO]  : {remote_url}")
                    remote_resources = await self._load_remote_resource(remote_url)
                    if remote_resources:
                        all_resources.update(remote_resources)
                        remote_count += 1
                        print(f"[SUCCESS] : {remote_url}")
                except Exception as e:
                    print(f"[ERROR]  {remote_url}: {e}")
            
            if remote_count > 0:
                print(f"[SUCCESS] ,  {remote_count} ")
            
            # 
            total_categories = len(all_resources)
            total_channels = sum(len(channels) for channels in all_resources.values())
            total_urls = sum(len(urls) for channels in all_resources.values() for urls in channels.values())
            
            print(f"\n[STATS] Step1 :")
            print(f"  : {total_categories}")
            print(f"  : {total_channels}")
            print(f"  URL: {total_urls}")
            
            #  step1_all_resources.csv (, URL)
            await self._save_step1_output(all_resources)
            
            print(f"\n[COMPLETE] Step1 ! : step1_all_resources.csv")
            
        except Exception as e:
            print(f"[ERROR] Step1 : {e}")
            import traceback
            traceback.print_exc()
    
    async def _load_m3u_file(self, filename):
        """ M3U """
        resources = {}
        file_path = Path(filename)
        
        if not file_path.exists():
            print(f"[WARNING] : {filename}")
            return resources
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_category = "Default"
            channel_name = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('#EXTINF:'):
                    parts = line.split(',')
                    if len(parts) > 1:
                        channel_name = parts[-1].strip()
                    else:
                        channel_name = line.strip()
                
                elif line.startswith('#EXTGRP:'):
                    current_category = line.replace('#EXTGRP:', '').strip()
                
                elif line and not line.startswith('#'):
                    if channel_name:
                        if current_category not in resources:
                            resources[current_category] = {}
                        if channel_name not in resources[current_category]:
                            resources[current_category][channel_name] = []
                        resources[current_category][channel_name].append(line)
                        channel_name = ""
            
            print(f"[INFO] M3U: {len(resources)} ")
            
        except Exception as e:
            print(f"[ERROR] M3U {filename}: {e}")
        
        return resources
    
    async def _load_txt_file(self, filename):
        """ TXT """
        resources = {}
        file_path = Path(filename)
        
        if not file_path.exists():
            print(f"[WARNING] : {filename}")
            return resources
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_category = "Default"
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if ',' in line:
                    parts = line.split(',', 1)
                    channel_name = parts[0].strip()
                    url = parts[1].strip()
                else:
                    url = line
                    channel_name = f"Channel_{line_num}"
                
                if current_category not in resources:
                    resources[current_category] = {}
                if channel_name not in resources[current_category]:
                    resources[current_category][channel_name] = []
                resources[current_category][channel_name].append(url)
            
            print(f"[INFO] TXT: {len(resources)} ")
            
        except Exception as e:
            print(f"[ERROR] TXT {filename}: {e}")
        
        return resources
    
    async def _load_remote_resource(self, url):
        """ URL """
        resources = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        if content.startswith('#EXTM3U'):
                            temp_file = Path("temp_remote.m3u")
                            with open(temp_file, 'w', encoding='utf-8') as f:
                                f.write(content)
                            resources = await self._load_m3u_file(str(temp_file))
                            temp_file.unlink()
                        else:
                            lines = content.split('\n')
                            current_category = "Remote"
                             
                            for line_num, line in enumerate(lines, 1):
                                line = line.strip()
                                if not line or line.startswith('#'):
                                    continue
                                 
                                if ',' in line:
                                    parts = line.split(',', 1)
                                    channel_name = parts[0].strip()
                                    url = parts[1].strip()
                                else:
                                    url = line
                                    channel_name = f"Remote_Channel_{line_num}"
                                 
                                if current_category not in resources:
                                    resources[current_category] = {}
                                if channel_name not in resources[current_category]:
                                    resources[current_category][channel_name] = []
                                resources[current_category][channel_name].append(url)
            
            print(f"[SUCCESS] : {url}")
            
        except Exception as e:
            print(f"[ERROR]  {url}: {e}")
        
        return resources
    
    async def _save_step1_output(self, all_resources):
        """ step1_all_resources.csv (, URL) - """
        filepath = self.output_dir / "step1_all_resources.csv"
        
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['', 'URL'])
                
                for category, channels in all_resources.items():
                    for channel_name, urls in channels.items():
                        for url in urls:
                            writer.writerow([channel_name, url])
            
            print(f"[INFO] : {filepath}")
            
            # 
            total_channels = sum(len(channels) for channels in all_resources.values())
            total_urls = sum(len(urls) for channels in all_resources.values() for urls in channels.values())
            
            print(f"[STATS] :")
            print(f"  : step1_all_resources.csv")
            print(f"  : , URL")
            print(f"  : {total_urls}")
            print(f"  URL: {total_urls}")
            
        except Exception as e:
            print(f"[ERROR] : {e}")
    
    def _get_current_time(self):
        """""" 
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    async def run_step3_deduplicate(self):
        """Step3: URL"""
        try:
            print("=" * 80)
            print(f" IPTV  - Step3 : {self._get_current_time()}")
            print("=" * 80)
            
            print("\n[Step3] URL...")
            
            #  Step1 
            step1_file = "output/step1_all_resources.csv"
            if not Path(step1_file).exists():
                print(f"[ERROR] Step1 : {step1_file}")
                print(" Step1")
                return
            
            #  Step1 
            all_resources = []
            try:
                with open(step1_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # 
                    
                    for row in reader:
                        if len(row) >= 2 and row[1].strip().startswith('http'):
                            resource = {
                                'name': row[0].strip(),
                                'url': row[1].strip(),
                                'category': 'Default'
                            }
                            all_resources.append(resource)
                
                print(f"[INFO] Step1 : {len(all_resources)} ")
            
            except Exception as e:
                print(f"[ERROR] Step1 : {e}")
                return
            
            # 
            print("[INFO]  URL...")
            unique_resources = await self._deduplicate_urls(all_resources)
            
            # 
            print(f"[STATS] :")
            print(f"  : {len(all_resources)}")
            print(f"  : {len(unique_resources)}")
            print(f"  : {len(all_resources) - len(unique_resources)}")
            print(f"  : {(len(all_resources) - len(unique_resources)) / len(all_resources) * 100:.1f}%")
            
            #  Step3 
            await self._save_step3_output(unique_resources)
            
            print(f"\n[COMPLETE] Step3 ! : step3_unique_resources.csv")
            
        except Exception as e:
            print(f"[ERROR] Step3 : {e}")
            import traceback
            traceback.print_exc()
    
    async def _deduplicate_urls(self, resources):
        """URL - """
        url_to_best_resource = {}
        
        for resource in resources:
            url = resource.get('url', '')
            if not url:
                continue
            
            name = resource.get('name', '')
            category = resource.get('category', '')
            
            #  URL 
            if url not in url_to_best_resource:
                url_to_best_resource[url] = {'name': name, 'category': category}
            else:
                #  - 
                existing_name = url_to_best_resource[url]['name']
                
                #  - 
                if len(name) > len(existing_name):
                    url_to_best_resource[url] = {'name': name, 'category': category}
                #  - 
                elif len(name) == len(existing_name):
                    existing_alpha = sum(c.isalnum() for c in existing_name)
                    new_alpha = sum(c.isalnum() for c in name)
                    if new_alpha > existing_alpha:
                        url_to_best_resource[url] = {'name': name, 'category': category}
        
        # 
        unique_resources = []
        for url, info in url_to_best_resource.items():
            resource = {
                'name': info['name'],
                'url': url,
                'category': info['category']
            }
            unique_resources.append(resource)
        
        return unique_resources
    
    async def _save_step3_output(self, unique_resources):
        """ step3_unique_resources.csv"""
        filepath = self.output_dir / "step3_unique_resources.csv"
        
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['', 'URL'])
                
                for resource in unique_resources:
                    writer.writerow([resource.get('name', ''), resource.get('url', '')])
            
            print(f"[INFO] : {filepath}")
            
            # 
            print(f"[STATS] :")
            print(f"  : step3_unique_resources.csv")
            print(f"  : , URL")
            print(f"  : {len(unique_resources)}")
            
        except Exception as e:
            print(f"[ERROR] : {e}")
    
    async def _run_conversion_tools(self):
        """运行转换工具 - 第三步专用，将exe复制到output目录"""
        import subprocess
        import shutil
        from pathlib import Path
        
        # 获取最新的文件
        output_dir = Path("output")
        utils_dir = Path("utils")
        
        #  Python 
        py_source = Path("utils/txt_to_m3u8b.py")  # Python 
        
        #  Python 
        if not py_source.exists():
            print(f" Python : {py_source}")
            return
        
        #  LE.txt  LU.txt 
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
                
        if le_file.exists():
            print(f" LE.txt -> LE.m3u")
            try:
                #  Python 
                try:
                    le_txt_path = output_dir / "LE.txt"
                    le_m3u_path = output_dir / "LE.m3u"
                    result = subprocess.run(["python", str(py_source), str(le_txt_path), str(le_m3u_path)], 
                                         check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    print(f" LE.m3u (Python)")
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    print(f" Python: {str(e)}")
                    
            except Exception as e:
                print(f" : {e}")
        
        if lu_file.exists():
            print(f" LU.txt -> LU.m3u")
            try:
                #  Python 
                try:
                    lu_txt_path = output_dir / "LU.txt"
                    lu_m3u_path = output_dir / "LU.m3u"
                    result = subprocess.run(["python", str(py_source), str(lu_txt_path), str(lu_m3u_path)], 
                                         check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    print(f" LU.m3u (Python)")
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    print(f" Python: {str(e)}")
                    
            except Exception as e:
                print(f" : {e}")
    
    async def _generate_results(self, video_resources: List[dict]):
        """生成最终结果文件 - 按照name_filtering_rules.txt模板编排"""
        from pathlib import Path
        from datetime import datetime
        import re
        
        # 创建输出目录
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 读取白名单资源
        whitelist_resources = self._load_whitelist_resources()
        
        # 合并资源：Step6资源 + 白名单资源
        all_resources = video_resources + whitelist_resources
        
        # 按速度分类
        le_resources = []  # >= 1.0 MB/s
        lu_resources = []  # >= 0.2 MB/s
        
        for resource in all_resources:
            speed = resource.get('speed', 0)
            if speed >= 1.0:
                le_resources.append(resource)
            if speed >= 0.2:
                lu_resources.append(resource)
        
        # 读取模板文件
        template_file = Path("name_filtering_rules.txt")
        if not template_file.exists():
            print(f"❌ 模板文件不存在：{template_file}")
            return
        
        with open(template_file, 'r', encoding='utf-8') as f:
            template_lines = f.readlines()
        
        # 解析模板
        template_structure = self._parse_template(template_lines)
        
        # 生成文件
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
        le_count = self._generate_file_by_template(le_file, le_resources, template_structure, "LE")
        lu_count = self._generate_file_by_template(lu_file, lu_resources, template_structure, "LU")
        
        # 统计信息
        total_channels = len(set(r['name'] for r in video_resources))
        le_unique_channels = len(set(r['name'] for r in le_resources))
        lu_unique_channels = len(set(r['name'] for r in lu_resources))
        
        print(f"✅ 生成 LE.txt: {le_count} 个资源 (>= 1.0 MB/s)")
        print(f"✅ 生成 LU.txt: {lu_count} 个资源 (>= 0.2 MB/s)")
        print(f"   good: 总频道={total_channels}, LE符合条件={le_unique_channels}, LU符合条件={lu_unique_channels}")
        print(f"📊 文件生成完成: LE.txt + LU.txt (按模板编排)")
    
    def _parse_template(self, template_lines):
        """解析模板文件结构"""
        structure = []
        current_category = None
        current_keywords = []
        
        for line in template_lines:
            line = line.strip()
            
            if not line:  # 空行
                structure.append({'type': 'empty', 'content': ''})
                continue
            
            if '#genre#' in line:
                # 保存前一个分类
                if current_category:
                    structure.append({
                        'type': 'category',
                        'name': current_category,
                        'keywords': current_keywords
                    })
                
                # 开始新分类
                current_category = line.split('#genre#')[0].strip()
                current_keywords = []
                structure.append({'type': 'header', 'content': line})
            elif current_category and line:
                # 关键词
                current_keywords.append(line)
        
        # 保存最后一个分类
        if current_category:
            structure.append({
                'type': 'category',
                'name': current_category,
                'keywords': current_keywords
            })
        
        return structure
    
    def _generate_file_by_template(self, output_file, resources, template_structure, file_type):
        """按照模板生成文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            total_count = 0
            
            for item in template_structure:
                if item['type'] == 'empty':
                    f.write('\n')
                elif item['type'] == 'header':
                    f.write(item['content'] + '\n')
                elif item['type'] == 'category':
                    # 按关键词分类资源
                    category_resources = self._classify_resources_by_keywords(
                        resources, item['keywords']
                    )
                    
                    # 排序资源
                    sorted_resources = self._sort_resources(category_resources)
                    
                    # 写入资源
                    for resource in sorted_resources:
                        f.write(f"{resource['name']},{resource['url']}\n")
                        total_count += 1
            
            return total_count
    
    def _classify_resources_by_keywords(self, resources, keywords):
        """按关键词分类资源，按规则前后顺序优先"""
        classified_resources = []
        used_resources = set()  # 记录已使用的资源，避免重复
        
        for keyword in keywords:
            for resource in resources:
                resource_id = (resource['name'], resource['url'])  # 使用名称+URL作为唯一标识
                
                if resource_id not in used_resources:
                    # 修正CCTV4k为CCTV 4k内容识别
                    resource_name = resource['name'].replace('CCTV4k', 'CCTV 4k')
                    
                    if keyword.lower() in resource_name.lower():
                        # 创建新的资源对象，更新名称
                        new_resource = resource.copy()
                        new_resource['name'] = resource_name
                        classified_resources.append(new_resource)
                        used_resources.add(resource_id)
        
        return classified_resources
    
    def _sort_resources(self, resources):
        """ sorting resources - implement user's specific sorting requirements"""
        if not resources:
            return []
        
        # function to extract CCTV number for sorting
        def extract_cctv_number(name):
            # handle CCTV-数字 format (e.g., CCTV-1, CCTV-2)
            match = re.search(r'CCTV-(\d+)', name, re.IGNORECASE)
            if match:
                return int(match.group(1))
            
            # handle CCTV数字 format (e.g., CCTV1, CCTV2)
            match = re.search(r'CCTV(\d+)', name, re.IGNORECASE)
            if match:
                return int(match.group(1))
            
            return 999999  # for non-CCTV channels
        
        # function to identify 4k content
        def is_4k_content(name):
            name_lower = name.lower()
            return '4k' in name_lower or 'cctv4k' in name_lower
        
        # first, group resources by name (case-sensitive)
        name_groups = {}
        for resource in resources:
            name = resource['name']
            if name not in name_groups:
                name_groups[name] = []
            name_groups[name].append(resource)
        
        # sort each name group: whitelist first, then by speed descending
        for name, group in name_groups.items():
            group.sort(key=lambda r: (
                0 if r.get('is_whitelist', False) else 1,  # whitelist priority
                -r.get('speed', 0)  # speed descending
            ))
        
        # sort names with special logic for CCTV channels
        def sort_key(name):
            # check if it's a 4k content
            if is_4k_content(name):
                cctv_num = extract_cctv_number(name)
                if cctv_num != 999999:
                    # CCTV4k gets special treatment: put 4k content at the end of CCTV channels
                    return (0, cctv_num, 999999)  # (is_cctv, cctv_number, 4k_priority)
                else:
                    # non-CCTV 4k content
                    return (1, name, 0)  # (is_cctv, name, 4k_priority)
            else:
                cctv_num = extract_cctv_number(name)
                if cctv_num != 999999:
                    # regular CCTV channels
                    return (0, cctv_num, 0)  # (is_cctv, cctv_number, 4k_priority)
                else:
                    # non-CCTV channels, sort lexicographically
                    return (1, name, 0)  # (is_cctv, name, 4k_priority)
        
        sorted_names = sorted(name_groups.keys(), key=sort_key)
        
        # flatten the sorted groups
        sorted_resources = []
        for name in sorted_names:
            sorted_resources.extend(name_groups[name])
        
        return sorted_resources
    
    def _load_whitelist_resources(self):
        """加载白名单资源，默认速度5MB/s"""
        whitelist_file = Path("white.txt")
        whitelist_resources = []
        
        if not whitelist_file.exists():
            print(f"⚠️ 白名单文件不存在：{whitelist_file}")
            return whitelist_resources
        
        try:
            with open(whitelist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            url = parts[1].strip()
                            
                            if name and url and url.startswith('http'):
                                resource = {
                                    'name': name,
                                    'url': url,
                                    'speed': 5.0,  # 白名单默认速度5MB/s
                                    'is_whitelist': True,
                                    'category': '白名单'
                                }
                                whitelist_resources.append(resource)
        
            print(f"✅ 加载白名单资源: {len(whitelist_resources)} 个")
        except Exception as e:
            print(f"❌ 加载白名单失败: {e}")
        
        return whitelist_resources
    
    async def _cleanup_output_directory(self):
        """清理output目录，删除不需要的文件，保留CSV中间文件和最终文件"""
        import glob
        from pathlib import Path
        
        output_dir = Path("output")
        
        # 需要保留的文件模式
        keep_patterns = [
            "step*.csv",           # 中间CSV文件
            "LE.txt", "LU.txt",    # 最终txt文件
            "LE.m3u", "LU.m3u",    # 最终m3u文件
            "txt_to_m3u8b.py",     # Python
            "ffmpeg.exe"             # FFmpeg
        ]
        
        # 需要删除的文件模式
        delete_patterns = [
            "live+*.txt",           # 分级txt文件（删除）
            "*.txt.bak", "*.csv.bak" # 备份文件（删除）
        ]
        
        # 注意：不删除live+*.csv，因为包含分级结果
        # 注意：不删除step*.csv，因为包含中间结果
        
        # 特别保护：确保txt_to_m3u8b.py不被删除
        py_file = output_dir / "txt_to_m3u8b.py"
        if py_file.exists():
            print(f" : txt_to_m3u8b.py")
        
        print(" 检查需要清理的文件...")
        
        deleted_count = 0
        for pattern in delete_patterns:
            files = glob.glob(str(output_dir / pattern))
            for file in files:
                try:
                    os.remove(file)
                    print(f"🗑️ 删除: {Path(file).name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️ 删除失败 {Path(file).name}: {e}")
        
        print(f"✅ 清理完成，删除了 {deleted_count} 个文件")
    
    async def run_from_step7(self):
        """从Step7开始运行"""
        try:
            main_start_time = time.time()
            
            print("=" * 80)
            print(f"【IPTV检测工具 - Step7及以后】开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"从step6_video_resources.csv开始运行")
            print("=" * 80)
            
            # 读取Step6结果文件
            step6_csv_path = "output/step6_video_resources.csv"
            if not os.path.exists(step6_csv_path):
                print(f"❌ Step6结果文件不存在：{step6_csv_path}")
                print(f"请先运行second.py完成Step6的工作")
                return
            
            print(f"\n📊 从Step7开始：读取Step6结果文件")
            print("-" * 50)
            
            video_resources = self._read_step6_csv_resources(step6_csv_path)
            
            if not video_resources:
                print("❌ 未读取到任何Step6资源")
                return
            
            print(f"✅ 成功读取 {len(video_resources)} 个Step6资源")
            
            # 清理output目录，只保留CSV中间文件
            print(f"\n🧹 清理output目录")
            print("-" * 50)
            await self._cleanup_output_directory()
            
            # Step7: 结果整理输出
            print(f"\n📊 Step7: 结果整理输出")
            print("-" * 50)
            
            await self._generate_results(video_resources)
            
            # Step8: 运行转换工具
            print(f"\n📊 Step8: 运行转换工具")
            print("-" * 50)
            
            await self._run_conversion_tools()
            
            # 最终统计
            main_end_time = time.time()
            print(f"\n🎉 检测完成！总耗时: {self._format_duration(main_end_time - main_start_time)}")
            print(f"📊 从Step7开始统计: Step6={len(video_resources)}")
            
        except Exception as e:
            print(f"❌ Step7及以后步骤失败: {e}")
            import traceback
            traceback.print_exc()
    
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
            
            # 解析资源行，格式：名称,URL,速度
            if ',' in line and not line.startswith('#'):
                try:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        url = parts[1].strip()
                        speed = 0.0  # 默认速度
                        
                        # 尝试从URL后面提取速度信息
                        if len(parts) >= 3:
                            try:
                                speed = float(parts[2].strip())
                            except ValueError:
                                pass
                        
                        if name and url and url.startswith('http'):
                            resource = {
                                'name': name,
                                'url': url,
                                'category': current_category,
                                'speed': speed,
                                'has_video': has_video,
                                'has_audio': has_audio,
                                'is_whitelist': False
                            }
                            resources.append(resource)
                except Exception:
                    pass
        
        return resources

async def main():
    """ """

    
    checker = ThirdChecker()
    
    # 

    await checker.run_from_step7()


if __name__ == "__main__":
    asyncio.run(main())
