#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL检测模块 - 基于IPTV API框架和异步网络检测
"""

import asyncio
import copy
import gc
import time
from typing import List, Dict, Any, Optional
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
    
    async def check_urls_batch(self, urls: List[str]) -> List[str]:
        """批量检查URL有效性"""
        logger.info(f"开始批量URL检测: {len(urls)}个URL")
        
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
            for i in range(0, len(urls_copy), self.batch_size):
                batch = urls_copy[i:i + self.batch_size]
                batch_results = await self._check_url_batch(batch)
                results.extend(batch_results)
                
                # IPTV API风格：批次间内存检查
                await self._check_memory()
                
                # 清理批次数据
                del batch
                gc.collect()
            
            # 过滤有效结果
            valid_urls = [result['url'] for result in results if result['is_valid']]
            
            logger.info(f"URL检测完成: 有效{len(valid_urls)}/{len(urls_copy)}个, "
                       f"缓存命中{self.cache_hits}次")
            
            return valid_urls
            
        finally:
            # 清理拷贝数据
            del urls_copy
            gc.collect()
    
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
    
    async def test_speed_batch(self, urls: List[str]) -> List[Any]:
        """批量速度测试"""
        logger.info(f"开始批量速度测试: {len(urls)}个URL")
        
        if not urls:
            return []
        
        # IPTV API风格：深拷贝避免内存污染
        urls_copy = copy.deepcopy(urls)
        
        try:
            # 分批处理
            results = []
            for i in range(0, len(urls_copy), self.batch_size):
                batch = urls_copy[i:i + self.batch_size]
                batch_results = await self._test_speed_batch(batch)
                results.extend(batch_results)
                
                # IPTV API风格：批次间内存检查
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
        """测试单个URL的速度"""
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
                
                timeout = aiohttp.ClientTimeout(total=config.speed_test_timeout)
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
                    total_size = 0
                    
                    async with session.get(url) as response:
                        if response.status == 200:
                            result['delay'] = int(round((time.time() - start_time) * 1000))
                            
                            # 下载前1MB测试速度
                            async for chunk in response.content.iter_any():
                                if chunk:
                                    total_size += len(chunk)
                                    if total_size >= 1024 * 1024:  # 1MB
                                        break
                            
                            total_time = time.time() - start_time
                            if total_time > 0:
                                result['speed'] = (total_size / total_time) / (1024 * 1024)  # MB/s
                
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
