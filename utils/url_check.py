#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL检测模块 - 基于IPTV API框架和异步网络检测
"""

import asyncio
import copy
import gc
import time
import aiohttp
import logging
from typing import List, Dict, Any, Optional, Callable
import logging

from .config import config
from .types import CheckResult, SpeedResult
from .tools import format_speed, is_valid_url

logger = logging.getLogger(__name__)


class URLChecker:
    """URL检测器 - 基于IPTV API框架"""
    
    def __init__(self):
        self.max_concurrent = config.max_concurrent
        self.timeout = config.url_check_timeout
        self.memory_threshold = config.memory_threshold
        self.batch_size = config.batch_size
        self.cache = {}
        self.cache_hits = 0
        
        # IPTV API风格的信号量控制
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 统计信息
        self.total_processed = 0
        self.success_count = 0
        self.error_count = 0
    
    async def check_urls_batch(self, urls: List[str], progress_callback: Callable[[int, int, int], None] = None) -> List[str]:
        """批量检查URL有效性"""
        logger.info(f"开始批量URL检测: {len(urls)}个")
        
        # IPTV API风格：深拷贝避免内存污染
        urls_copy = copy.deepcopy(urls)
        
        try:
            # 分批处理
            results = []
            processed_count = 0
            
            for i in range(0, len(urls_copy), self.batch_size):
                batch = urls_copy[i:i + self.batch_size]
                batch_results = await self._check_url_batch(batch)
                results.extend(batch_results)
                
                # 更新进度
                processed_count += len(batch)
                if progress_callback:
                    progress_callback(processed_count, len(urls_copy), len(batch_results))
                
                # IPTV API风格：批次间内存检查（每5批次检查一次）
                if i % 5 == 0:
                    await self._check_memory()
                
                # 清理批次数据
                del batch
                gc.collect()
            
            # 过滤有效URL
            valid_urls = [result['url'] for result in results if result['is_valid']]
            
            logger.info(f"URL检测完成: 有效{len(valid_urls)}/{len(urls_copy)}个, "
                       f"缓存命中{self.cache_hits}次")
            return valid_urls
            
        except Exception as e:
            logger.error(f"批量URL检测失败: {e}")
            return []
    
    async def _check_url_batch(self, urls: List[str]) -> List[CheckResult]:
        """检查单个批次的URL"""
        # IPTV API风格：创建并发任务
        tasks = [self._check_single_url(url) for url in urls]
        
        # IPTV API风格：使用asyncio.gather并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"URL检测异常: {result}")
                self.error_count += 1
            elif result and result['is_valid']:
                valid_results.append(result)
                self.success_count += 1
            else:
                self.error_count += 1
        
        return valid_results
    
    async def _check_single_url(self, url: str) -> CheckResult:
        """检查单个URL"""
        async with self.semaphore:
            # IPTV API风格：检查缓存
            cache_key = str(hash(url))
            if cache_key in self.cache:
                self.cache_hits += 1
                return self.cache[cache_key]
            
            result = {
                'url': url,
                'is_valid': False,
                'error': None,
                'response_time': None
            }
            
            try:
                # 使用异步HTTP检测
                import aiohttp
                
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                connector = aiohttp.TCPConnector(
                    limit=self.max_concurrent,
                    limit_per_host=5,
                    ttl_dns_cache=300,
                    use_dns_cache=True,
                    ssl=False
                )
                
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                ) as session:
                    
                    start_time = time.time()
                    async with session.head(url) as response:
                        result['response_time'] = (time.time() - start_time) * 1000
                        
                        # 检查状态码
                        if response.status == 200:
                            result['is_valid'] = True
                        elif response.status == 404:
                            result['error'] = f"HTTP 404 Not Found"
                        else:
                            result['is_valid'] = True  # 非404都认为有效
                
            except asyncio.TimeoutError:
                result['error'] = "Timeout"
            except aiohttp.ClientError as e:
                result['error'] = f"Client Error: {str(e)}"
            except Exception as e:
                result['error'] = f"Error: {str(e)}"
            
            # IPTV API风格：缓存结果
            if len(self.cache) < 1000:
                self.cache[cache_key] = result
            
            self.total_processed += 1
            return result
    
    async def test_speed_batch(self, urls: List[str], progress_callback: Optional[Callable] = None) -> List[Any]:
        """批量速度测试"""
        logger.info(f"开始批量速度测试: {len(urls)}个URL")
        
        if not urls:
            return []
        
        # IPTV API风格：深拷贝避免内存污染
        urls_copy = copy.deepcopy(urls)
        
        try:
            # 分批处理
            results = []
            valid_count = 0
            for i in range(0, len(urls_copy), self.batch_size):
                batch = urls_copy[i:i + self.batch_size]
                batch_results = await self._test_speed_batch(batch)
                results.extend(batch_results)
                valid_count += len([r for r in batch_results if r and r.get('speed', 0) > 0])
                
                # 调用进度回调
                if progress_callback:
                    current = min(i + self.batch_size, len(urls_copy))
                    progress_callback(current, len(urls_copy), valid_count)
                
                # IPTV API风格：批次间内存检查（每5批次检查一次）
                if i % 5 == 0:
                    await self._check_memory()
                
                # 清理批次数据
                del batch
                gc.collect()
            
            # 过滤有效结果
            valid_results = [result for result in results if result['speed'] > 0]
            
            logger.info(f"速度测试完成: 有效{len(valid_results)}/{len(urls_copy)}个")
            
            return valid_results
            
        finally:
            # 清理拷贝数据
            del urls_copy
            gc.collect()
    
    async def _test_speed_batch(self, urls: List[str]) -> List[SpeedResult]:
        """测试单个批次的速度"""
        # IPTV API风格：创建并发任务
        tasks = [self._test_single_speed(url) for url in urls]
        
        # IPTV API风格：使用asyncio.gather并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"速度测试异常: {result}")
            elif result and result['speed'] > 0:
                valid_results.append(result)
        
        return valid_results
    
    async def _test_single_speed(self, url: str) -> SpeedResult:
        """测试单个URL的速度 - 采用url-check-v-pro.py核心逻辑"""
        async with self.semaphore:
            result = {
                'url': url,
                'speed': 0.0,
                'delay': None,
                'error': None
            }
            
            try:
                # 使用异步HTTP下载测试
                import aiohttp
                
                # 采用url-check-v-pro.py的参数
                timeout = aiohttp.ClientTimeout(total=5)  # 5秒连接超时
                connector = aiohttp.TCPConnector(
                    limit=self.max_concurrent,
                    limit_per_host=5,
                    ttl_dns_cache=300,
                    use_dns_cache=True,
                    ssl=False
                )
                
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={'User-Agent': 'Mozilla/5.0'}
                ) as session:
                    
                    start_time = time.time()
                    total_size = 0
                    chunk_size = 10240  # url-check-v-pro.py的10KB块大小
                    
                    async with session.get(url) as response:
                        if response.status == 200:
                            result['delay'] = int(round((time.time() - start_time) * 1000))
                            
                            # url-check-v-pro.py核心逻辑：固定时间测试(3秒)
                            test_start_time = time.time()
                            chunk_count = 0
                            
                            async for chunk in response.content.iter_chunked(chunk_size):
                                if chunk:
                                    total_size += len(chunk)
                                    chunk_count += 1
                                
                                # 每读取10块检查一次时间，避免阻塞
                                if chunk_count >= 10:
                                    chunk_count = 0
                                    if time.time() - test_start_time >= 3:  # 3秒测试时间
                                        break
                                
                                # 严格3秒时间限制
                                if time.time() - test_start_time >= 3:
                                    break
                            
                            # url-check-v-pro.py速度计算：bytes/s
                            test_time = time.time() - test_start_time
                            if test_time > 0:
                                speed_bytes_per_sec = total_size / test_time
                                # 转换为MB/s保持与Step5一致
                                result['speed'] = speed_bytes_per_sec / (1024 * 1024)
                
            except asyncio.TimeoutError:
                result['error'] = "Timeout"
            except aiohttp.ClientError as e:
                result['error'] = f"Client Error: {str(e)}"
            except Exception as e:
                result['error'] = f"Error: {str(e)}"
            
            return result
    
    async def _check_memory(self):
        """检查内存使用"""
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            
            if memory_percent > self.memory_threshold:
                logger.warning(f"内存使用过高: {memory_percent:.1f}% > {self.memory_threshold}%")
                
                # IPTV API风格：多轮垃圾回收
                for i in range(3):
                    collected = gc.collect()
                    logger.debug(f"垃圾回收第{i+1}轮: 清理{collected}个对象")
                    await asyncio.sleep(0.1)
                
                # 清理缓存
                if len(self.cache) > 500:
                    self.cache.clear()
                    logger.info("清理内存缓存")
                
                # 再次检查
                after_gc = psutil.virtual_memory().percent
                logger.debug(f"回收后内存: {after_gc:.1f}%")
                
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
