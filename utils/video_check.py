#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频检测模块 - 基于IPTV API框架和画面检测
"""

import asyncio
import copy
import gc
import time
import subprocess
import json
import os
import sys
from typing import List, Dict, Any, Optional, Callable
import logging

from utils.config import config
from utils.iptv_types import VideoResult
from utils.tools import is_valid_url

logger = logging.getLogger(__name__)


class VideoChecker:
    """视频检测器 - 基于IPTV API框架"""
    
    def __init__(self):
        self.max_concurrent = min(config.max_concurrent, 2)  # 视频检测降低并发
        self.timeout = config.video_check_timeout
        self.memory_threshold = config.memory_threshold
        self.batch_size = min(config.batch_size, 10)  # 视频检测减小批次
        self.cache = {}
        self.cache_hits = 0
        
        # IPTV API风格的信号量控制
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 统计信息
        self.total_processed = 0
        self.success_count = 0
        self.error_count = 0
        
        # 检测worker脚本路径
        self.worker_script = self._get_worker_script()
    
    def _get_worker_script(self) -> str:
        """获取检测worker脚本路径"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 检测运行环境
        is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
        
        if is_github_actions:
            worker_path = os.path.join(base_dir, 'utils', 'video_check_worker_github.py')
        else:
            worker_path = os.path.join(base_dir, 'utils', 'video_check_worker.py')
        
        # 如果不存在，回退到标准版本
        if not os.path.exists(worker_path):
            worker_path = os.path.join(base_dir, 'utils', 'video_check_worker.py')
        
        logger.info(f"使用视频检测脚本: {worker_path}")
        return worker_path
    
    async def check_videos_batch(self, urls: List[str], progress_callback: Optional[Callable] = None) -> List[str]:
        """批量检查视频有效性"""
        logger.info(f"开始批量视频检测: {len(urls)}个URL")
        
        # 过滤有效URL
        valid_urls = [url for url in urls if is_valid_url(url)]
        logger.info(f"过滤后有效URL: {len(valid_urls)}个")
        
        if not valid_urls:
            return []
        
        # IPTV API风格：深拷贝避免内存污染
        urls_copy = copy.deepcopy(valid_urls)
        
        try:
            # 分批处理
            results = []
            valid_count = 0
            for i in range(0, len(urls_copy), self.batch_size):
                batch = urls_copy[i:i + self.batch_size]
                batch_results = await self._check_video_batch(batch)
                results.extend(batch_results)
                
                # 统计有效视频数 - 有画面变化或有声音
                batch_valid = len([result for result in batch_results if result['has_video'] or result['has_audio']])
                valid_count += batch_valid
                
                # 调用进度回调
                if progress_callback:
                    current = min(i + self.batch_size, len(urls_copy))
                    progress_callback(current, len(urls_copy), valid_count)
                
                # IPTV API风格：批次间内存检查
                await self._check_memory()
                
                # 清理批次数据
                del batch
                gc.collect()
            
            # 过滤有效结果 - 有画面变化或有声音
            valid_videos = [result for result in results if result['has_video'] or result['has_audio']]
            
            logger.info(f"视频检测完成: 有效{len(valid_videos)}/{len(urls_copy)}个, "
                       f"缓存命中{self.cache_hits}次")
            
            return valid_videos
            
        finally:
            # 清理拷贝数据
            del urls_copy
            gc.collect()
    
    async def _check_video_batch(self, urls: List[str]) -> List[VideoResult]:
        """检查单个批次的视频"""
        # IPTV API风格：创建并发任务
        tasks = [self._check_single_video(url) for url in urls]
        
        # IPTV API风格：使用asyncio.gather并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果 - 有画面变化或有声音
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"视频检测异常: {result}")
                self.error_count += 1
            elif result and (result['has_video'] or result['has_audio']):
                valid_results.append(result)
                self.success_count += 1
            else:
                self.error_count += 1
        
        return valid_results
    
    async def _check_single_video(self, url: str) -> VideoResult:
        """检查单个URL的视频"""
        async with self.semaphore:
            # IPTV API风格：检查缓存
            cache_key = str(hash(url))
            if cache_key in self.cache:
                self.cache_hits += 1
                return self.cache[cache_key]
            
            result = {
                'url': url,
                'has_video': False,
                'has_audio': False,
                'video_changing': False,
                'error': None
            }
            
            try:
                # 使用子进程调用视频检测worker
                cmd = [sys.executable, self.worker_script, url]
                
                # IPTV API风格：使用异步子进程
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    text=True
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), self.timeout)
                    
                    if proc.returncode == 0:
                        # 解析JSON结果
                        result = self._parse_video_result(stdout, url)
                    else:
                        result['error'] = f"检测失败: {stderr.strip()}"
                        
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    result['error'] = "检测超时"
                
            except Exception as e:
                result['error'] = f"检测异常: {str(e)}"
            
            # IPTV API风格：缓存结果
            if len(self.cache) < 500:  # 视频检测缓存更小
                self.cache[cache_key] = result
            
            self.total_processed += 1
            return result
    
    def _parse_video_result(self, output: str, url: str) -> VideoResult:
        """解析视频检测结果"""
        result = {
            'url': url,
            'has_video': False,
            'has_audio': False,
            'video_changing': False,
            'error': None
        }
        
        try:
            # 清理输出，提取JSON
            lines = output.strip().split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                stripped_line = line.strip()
                if stripped_line == '{':
                    in_json = True
                    json_lines.append(stripped_line)
                elif stripped_line == '}':
                    in_json = False
                    json_lines.append(stripped_line)
                elif in_json:
                    json_lines.append(stripped_line)
            
            json_str = '\n'.join(json_lines)
            
            if json_str:
                data = json.loads(json_str)
                
                result['has_video'] = data.get('has_video', False)
                result['has_audio'] = data.get('has_audio', False)
                result['video_changing'] = data.get('video_changing', False)
                result['error'] = data.get('error')
            else:
                result['error'] = "无法解析检测结果"
                
        except json.JSONDecodeError as e:
            result['error'] = f"JSON解析失败: {str(e)}"
        except Exception as e:
            result['error'] = f"解析异常: {str(e)}"
        
        return result
    
    async def _check_memory(self):
        """检查内存使用"""
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            
            # 视频检测使用更严格的内存阈值
            threshold = self.memory_threshold - 10
            
            if memory_percent > threshold:
                logger.warning(f"视频检测内存过高: {memory_percent:.1f}% > {threshold}%")
                
                # IPTV API风格：多轮垃圾回收
                for i in range(3):
                    collected = gc.collect()
                    logger.debug(f"视频检测垃圾回收第{i+1}轮: 清理{collected}个对象")
                    await asyncio.sleep(0.2)  # 视频检测等待更久
                
                # 清理缓存
                if len(self.cache) > 200:
                    self.cache.clear()
                    logger.info("清理视频检测缓存")
                
                # 再次检查
                after_gc = psutil.virtual_memory().percent
                logger.debug(f"视频检测回收后内存: {after_gc:.1f}%")
                
        except ImportError:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_processed': self.total_processed,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'cache_hits': self.cache_hits,
            'cache_size': len(self.cache)
        }
