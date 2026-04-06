#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源管理器 - 管理本地资源、白名单和远程资源
"""

import os
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Set
from utils.config import config

class ResourceManager:
    """资源管理器"""
    
    def __init__(self):
        self.local_resources = {}
        self.whitelist = set()
        self.remote_resources = {}
        
    async def load_all_resources(self):
        """加载所有资源"""
        print("开始加载资源...")
        
        # 1. 加载本地资源
        await self._load_local_resources()
        
        # 2. 加载白名单
        await self._load_whitelist()
        
        # 3. 加载远程资源
        await self._load_remote_resources()
        
        # 4. 合并所有资源
        merged_resources = self._merge_resources()
        
        print(f"资源加载完成！总计 {len(merged_resources)} 个频道")
        return merged_resources
    
    async def _load_local_resources(self):
        """加载本地资源"""
        print("加载本地资源...")
        
        # 加载resources.m3u
        if os.path.exists("resources.m3u"):
            m3u_resources = self._parse_m3u_file("resources.m3u")
            self._merge_into_resources(m3u_resources)
            print(f"   resources.m3u: {len(m3u_resources)} 个频道")
        
        # 加载resources.txt
        if os.path.exists("resources.txt"):
            txt_resources = self._parse_txt_file("resources.txt")
            self._merge_into_resources(txt_resources)
            print(f"   resources.txt: {len(txt_resources)} 个频道")
    
    async def _load_whitelist(self):
        """加载白名单"""
        print("加载白名单...")
        
        whitelist_file = config.whitelist_file
        if os.path.exists(whitelist_file):
            with open(whitelist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.whitelist.add(line.lower())
            print(f"   {whitelist_file}: {len(self.whitelist)} 个白名单规则")
        else:
            print(f"   白名单文件不存在: {whitelist_file}")
    
    async def _load_remote_resources(self):
        """加载远程资源 - 从网上获取name与url"""
        print("从网上获取远程资源...")
        
        remote_file = "resources_remote.txt"
        if os.path.exists(remote_file):
            # 读取远程资源文件中的URL
            remote_urls = self._extract_urls_from_remote_file(remote_file)
            print(f"   发现 {len(remote_urls)} 个远程URL")
            
            # 从网上获取详细信息
            detailed_resources = await self._fetch_detailed_resources(remote_urls)
            self._merge_into_resources(detailed_resources)
            print(f"   获取到 {len(detailed_resources)} 个有效频道")
        else:
            print(f"   远程资源文件不存在: {remote_file}")
    
    def _extract_urls_from_remote_file(self, file_path: str) -> List[str]:
        """从远程资源文件中提取URL"""
        urls = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 提取URL
                if ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        url = parts[1].strip()
                        if url.startswith('http'):
                            urls.append(url)
                elif line.startswith('http'):
                    urls.append(line)
        
        return list(set(urls))  # 去重
    
    async def _fetch_detailed_resources(self, urls: List[str]) -> Dict:
        """获取详细的远程资源信息 - 实际下载内容"""
        detailed_resources = {}
        
        async with aiohttp.ClientSession() as session:
            # 并发获取详细信息
            tasks = [self._fetch_channel_details(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for result in results:
                if isinstance(result, dict) and result.get('valid'):
                    category = result.get('category', '其它')
                    resources = result.get('resources', [])
                    
                    # 将解析出的资源添加到结果中
                    for resource in resources:
                        name = resource.get('name', '未知频道')
                        url = resource.get('url', '')
                        
                        if category not in detailed_resources:
                            detailed_resources[category] = {}
                        if name not in detailed_resources[category]:
                            detailed_resources[category][name] = []
                        detailed_resources[category][name].append({'url': url})
        
        return detailed_resources
    
    async def _fetch_channel_details(self, session: aiohttp.ClientSession, url: str) -> Dict:
        """获取频道详细信息 - 实际下载和解析远程资源内容"""
        try:
            # 下载远程资源内容
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    content = await response.text(encoding='utf-8', errors='ignore')
                    
                    # 解析内容获取多个name-url对
                    resources = self._parse_remote_content(content, url)
                    
                    if resources:
                        return {
                            'valid': True,
                            'url': url,
                            'resources': resources,  # 返回解析出的资源列表
                            'category': '其它'  # 远程资源默认分类为其它
                        }
                    else:
                        return {
                            'valid': False,
                            'url': url,
                            'name': '无有效资源',
                            'category': '其它'
                        }
        except Exception as e:
            print(f"[调试] 获取远程资源失败: {url} - {e}")
            pass
        
        return {
            'valid': False,
            'url': url,
            'name': '获取失败',
            'category': '其它'
        }
    
    def _parse_remote_content(self, content: str, source_url: str) -> List[Dict]:
        """解析远程资源内容，提取name-url对 - 支持txt和m3u格式"""
        resources = []
        
        # 检查是否为M3U格式
        if content.startswith('#EXTM3U'):
            return self._parse_m3u_content(content, source_url)
        else:
            return self._parse_txt_content(content, source_url)
    
    def _parse_txt_content(self, content: str, source_url: str) -> List[Dict]:
        """解析TXT格式内容"""
        resources = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 解析格式：频道名,URL
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) >= 2:
                    name = parts[0].strip()
                    url = parts[1].strip()
                    
                    # 验证URL格式
                    if name and url and url.startswith('http'):
                        resources.append({
                            'name': name,
                            'url': url,
                            'source': f'remote:{source_url}',
                            'category': '其它'
                        })
        
        return resources
    
    def _parse_m3u_content(self, content: str, source_url: str) -> List[Dict]:
        """解析M3U格式内容"""
        resources = []
        lines = content.split('\n')
        current_name = ""
        
        for line in lines:
            line = line.strip()
            
            # 解析EXTINF行获取频道名称
            if line.startswith('#EXTINF:'):
                # 格式: #EXTINF:-1,频道名称
                if ',' in line:
                    name_part = line.split(',', 1)[1].strip()
                    current_name = name_part
                else:
                    current_name = ""
            
            # 解析URL行
            elif line.startswith('#') or not line:
                continue
            else:
                url = line.strip()
                
                # 验证URL格式
                if url.startswith('http'):
                    name = current_name if current_name else self._extract_name_from_url(url)
                    
                    resources.append({
                        'name': name,
                        'url': url,
                        'source': f'remote:{source_url}',
                        'category': '其它'
                    })
                
                current_name = ""  # 重置名称
        
        return resources
    
    def _extract_name_from_url(self, url: str) -> str:
        """从URL中提取名称作为备用"""
        try:
            # 从URL路径中提取文件名或路径名
            url_parts = url.split('/')
            if len(url_parts) > 1:
                filename = url_parts[-1]
                if '.' in filename:
                    filename = filename.split('.')[0]
                return filename
            return "未知频道"
        except:
            return "未知频道"
    
    def _infer_channel_info(self, url: str) -> Dict:
        """根据URL推断频道信息"""
        url_lower = url.lower()
        
        # 央视频道
        if 'cctv' in url_lower:
            for cctv_num in ['1', '2', '3', '4', '5', '6', '13']:
                if f'cctv{cctv_num}' in url_lower:
                    return {'name': f'CCTV{cctv_num}', 'category': '央视'}
            if 'cctvxw' in url_lower:
                return {'name': 'CCTV新闻', 'category': '央视'}
            return {'name': 'CCTV频道', 'category': '央视'}
        
        # 卫视频道
        elif any(tv in url_lower for tv in ['hunantv', 'zhejiangtv', 'jiangsutv', 'dfws', 'gdws', 'scws', 'sdws', 'hbws']):
            if 'hunantv' in url_lower:
                return {'name': '湖南卫视', 'category': '卫视'}
            elif 'zhejiangtv' in url_lower:
                return {'name': '浙江卫视', 'category': '卫视'}
            elif 'jiangsutv' in url_lower:
                return {'name': '江苏卫视', 'category': '卫视'}
            elif 'dfws' in url_lower:
                return {'name': '东方卫视', 'category': '卫视'}
            elif 'gdws' in url_lower:
                return {'name': '广东卫视', 'category': '卫视'}
            elif 'scws' in url_lower:
                return {'name': '四川卫视', 'category': '卫视'}
            elif 'sdws' in url_lower:
                return {'name': '山东卫视', 'category': '卫视'}
            elif 'hbws' in url_lower:
                return {'name': '湖北卫视', 'category': '卫视'}
            else:
                return {'name': '卫视频道', 'category': '卫视'}
        
        # 港澳台频道
        elif any(hk in url_lower for hk in ['rthklive', 'livestream']):
            if 'rthklive' in url_lower:
                return {'name': '香港电台', 'category': '港澳台'}
            else:
                return {'name': '港澳台频道', 'category': '港澳台'}
        
        # 欧美频道
        elif any(intl in url_lower for intl in ['bbci', 'cnn', 'fox', 'nbc', 'cbs', 'abc']):
            if 'bbci' in url_lower:
                return {'name': 'BBC', 'category': '欧美'}
            elif 'cnn' in url_lower:
                return {'name': 'CNN', 'category': '欧美'}
            elif 'fox' in url_lower:
                return {'name': 'FOX', 'category': '欧美'}
            elif 'nbc' in url_lower:
                return {'name': 'NBC', 'category': '欧美'}
            elif 'cbs' in url_lower:
                return {'name': 'CBS', 'category': '欧美'}
            elif 'abc' in url_lower:
                return {'name': 'ABC', 'category': '欧美'}
            else:
                return {'name': '欧美频道', 'category': '欧美'}
        
        # 其他国际频道
        elif any(other in url_lower for other in ['nhk', 'rt', 'france24', 'deutschewelle']):
            if 'nhk' in url_lower:
                return {'name': 'NHK', 'category': '欧美'}
            elif 'rt' in url_lower:
                return {'name': 'RT', 'category': '欧美'}
            elif 'france24' in url_lower:
                return {'name': 'France24', 'category': '欧美'}
            elif 'deutschewelle' in url_lower:
                return {'name': 'DeutscheWelle', 'category': '欧美'}
            else:
                return {'name': '国际频道', 'category': '欧美'}
        
        # 默认分类
        else:
            # 特殊处理txt文件
            if url_lower.endswith('.txt'):
                # 从URL中提取有意义的名称
                if 'livelite' in url_lower:
                    return {'name': 'livelite直播源', 'category': '其它'}
                elif '39183918' in url_lower:
                    return {'name': '39183918直播源', 'category': '其它'}
                elif 'gmbbk' in url_lower:
                    return {'name': 'gmbbk直播源', 'category': '其它'}
                else:
                    # 从URL路径中提取文件名作为名称
                    url_parts = url.split('/')
                    if len(url_parts) > 1:
                        filename = url_parts[-1].replace('.txt', '')
                        return {'name': filename, 'category': '其它'}
                    else:
                        return {'name': '直播源', 'category': '其它'}
            else:
                return {'name': '其他频道', 'category': '其它'}
    
    def _parse_m3u_file(self, file_path: str) -> Dict:
        """解析M3U文件"""
        resources = {}
        current_category = "默认分类"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('#EXTINF:'):
                    # 提取频道名称
                    if ',' in line:
                        channel_name = line.split(',')[-1].strip()
                        current_category = "默认分类"
                elif line.startswith('http') and 'channel_name' in locals():
                    # URL行
                    if current_category not in resources:
                        resources[current_category] = {}
                    if channel_name not in resources[current_category]:
                        resources[current_category][channel_name] = []
                    resources[current_category][channel_name].append({'url': line})
                    del locals()['channel_name']
        
        return resources
    
    def _parse_txt_file(self, file_path: str) -> Dict:
        """解析TXT文件"""
        resources = {}
        current_category = "默认分类"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                if "#genre#" in line:
                    current_category = line.split(",")[0].replace("#genre#", "").strip()
                elif "," in line:
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        channel_name, url = parts
                        if current_category not in resources:
                            resources[current_category] = {}
                        if channel_name not in resources[current_category]:
                            resources[current_category][channel_name] = []
                        resources[current_category][channel_name].append({'url': url})
        
        return resources
    
    async def _fetch_remote_urls(self, remote_resources: Dict) -> Dict:
        """从网络获取远程URL"""
        valid_resources = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for category, channels in remote_resources.items():
                for channel_name, urls in channels.items():
                    for url_info in urls:
                        url = url_info['url']
                        task = self._check_url(session, url, category, channel_name)
                        tasks.append(task)
            
            # 并发检查URL
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for result in results:
                if isinstance(result, dict) and result.get('valid'):
                    category = result['category']
                    channel_name = result['channel_name']
                    url = result['url']
                    
                    if category not in valid_resources:
                        valid_resources[category] = {}
                    if channel_name not in valid_resources[category]:
                        valid_resources[category][channel_name] = []
                    valid_resources[category][channel_name].append({'url': url})
        
        return valid_resources
    
    async def _check_url(self, session: aiohttp.ClientSession, url: str, category: str, channel_name: str) -> Dict:
        """检查URL是否有效"""
        try:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    return {
                        'valid': True,
                        'category': category,
                        'channel_name': channel_name,
                        'url': url
                    }
        except Exception:
            pass
        
        return {
            'valid': False,
            'category': category,
            'channel_name': channel_name,
            'url': url
        }
    
    def _merge_into_resources(self, new_resources: Dict):
        """合并资源"""
        for category, channels in new_resources.items():
            if category not in self.local_resources:
                self.local_resources[category] = {}
            
            for channel_name, urls in channels.items():
                if channel_name not in self.local_resources[category]:
                    self.local_resources[category][channel_name] = []
                
                for url_info in urls:
                    if url_info not in self.local_resources[category][channel_name]:
                        self.local_resources[category][channel_name].append(url_info)
    
    def _merge_resources(self) -> Dict:
        """合并所有资源并应用白名单过滤"""
        merged_resources = {}
        
        for category, channels in self.local_resources.items():
            filtered_channels = {}
            
            for channel_name, urls in channels.items():
                filtered_urls = []
                
                for url_info in urls:
                    url = url_info['url']
                    
                    # 应用白名单过滤
                    if self._is_whitelisted(url, channel_name):
                        filtered_urls.append(url_info)
                
                if filtered_urls:
                    filtered_channels[channel_name] = filtered_urls
            
            if filtered_channels:
                merged_resources[category] = filtered_channels
        
        return merged_resources
    
    def _is_whitelisted(self, url: str, channel_name: str) -> bool:
        """检查是否在白名单中"""
        if not self.whitelist:
            return True
        
        url_lower = url.lower()
        name_lower = channel_name.lower()
        
        # 检查域名匹配
        for rule in self.whitelist:
            if rule in url_lower or rule in name_lower:
                return True
        
        return False
