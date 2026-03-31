#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# async_network_checker.py - 基于IPTV API模式的高效网络检测

import asyncio
import aiohttp
import time
import copy
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import urlparse
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncNetworkChecker:
    """基于IPTV API模式的异步网络检测器"""
    
    def __init__(self, max_concurrent: int = 20, timeout: int = 10):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
        
        # 统计信息
        self.total_processed = 0
        self.success_count = 0
        self.error_count = 0
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
            ssl=False
        )
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def check_url_404_async(self, url: str) -> Dict[str, Any]:
        """异步检查URL是否404"""
        async with self.semaphore:
            result = {
                'url': url,
                'is_valid': False,
                'status_code': None,
                'error': None,
                'response_time': 0
            }
            
            start_time = time.time()
            
            try:
                async with self.session.head(url, allow_redirects=True) as response:
                    result['status_code'] = response.status
                    result['response_time'] = time.time() - start_time
                    
                    # 检查是否为有效状态码
                    if response.status == 200:
                        result['is_valid'] = True
                    elif response.status == 404:
                        result['error'] = '404 Not Found'
                    elif response.status in [301, 302, 303, 307, 308]:
                        # 重定向状态码，认为是有效的
                        result['is_valid'] = True
                    elif 400 <= response.status < 500:
                        result['error'] = f'Client Error {response.status}'
                    elif 500 <= response.status < 600:
                        result['error'] = f'Server Error {response.status}'
                    else:
                        result['is_valid'] = True  # 其他状态码暂时认为有效
                        
            except asyncio.TimeoutError:
                result['error'] = 'Timeout'
                result['response_time'] = self.timeout
            except aiohttp.ClientError as e:
                result['error'] = f'Client Error: {str(e)}'
            except Exception as e:
                result['error'] = f'Unexpected Error: {str(e)}'
            
            # 更新统计
            self.total_processed += 1
            if result['is_valid']:
                self.success_count += 1
            else:
                self.error_count += 1
                
            return result
    
    async def check_url_speed_async(self, url: str) -> Dict[str, Any]:
        """异步检测URL速度"""
        async with self.semaphore:
            result = {
                'url': url,
                'speed': 0,
                'delay': 0,
                'status_code': None,
                'error': None,
                'content_length': 0
            }
            
            start_time = time.time()
            
            try:
                async with self.session.get(url, allow_redirects=True) as response:
                    result['status_code'] = response.status
                    result['delay'] = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        # 下载前1MB来测试速度
                        content_length = 0
                        download_start = time.time()
                        
                        async for chunk in response.content.iter_chunked(8192):
                            content_length += len(chunk)
                            # 限制下载量为1MB
                            if content_length >= 1024 * 1024:
                                break
                        
                        download_time = time.time() - download_start
                        if download_time > 0:
                            result['speed'] = (content_length / download_time) / 1024 / 1024  # MB/s
                        result['content_length'] = content_length
                    else:
                        result['error'] = f'HTTP {response.status}'
                        
            except asyncio.TimeoutError:
                result['error'] = 'Timeout'
                result['delay'] = self.timeout * 1000
            except aiohttp.ClientError as e:
                result['error'] = f'Client Error: {str(e)}'
            except Exception as e:
                result['error'] = f'Unexpected Error: {str(e)}'
            
            # 更新统计
            self.total_processed += 1
            if result['speed'] > 0:
                self.success_count += 1
            else:
                self.error_count += 1
                
            return result
    
    async def batch_check_404(self, urls: List[str], 
                            callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """批量检查404"""
        logger.info(f"开始批量404检测: {len(urls)}个URL")
        
        tasks = [
            asyncio.create_task(self.check_url_404_async(url))
            for url in urls
        ]
        
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            results.append(result)
            
            # 进度回调
            if callback:
                callback(i + 1, len(urls), result)
            
            # 简单进度显示
            if (i + 1) % 50 == 0 or i + 1 == len(urls):
                progress = ((i + 1) / len(urls)) * 100
                logger.info(f"404检测进度: {i + 1}/{len(urls)} ({progress:.1f}%)")
        
        valid_urls = [r for r in results if r['is_valid']]
        logger.info(f"404检测完成: 有效{len(valid_urls)}/{len(urls)}个URL")
        
        return results
    
    async def batch_check_speed(self, urls: List[str], 
                              callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """批量检测速度"""
        logger.info(f"开始批量速度检测: {len(urls)}个URL")
        
        tasks = [
            asyncio.create_task(self.check_url_speed_async(url))
            for url in urls
        ]
        
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            results.append(result)
            
            # 进度回调
            if callback:
                callback(i + 1, len(urls), result)
            
            # 简单进度显示
            if (i + 1) % 20 == 0 or i + 1 == len(urls):
                progress = ((i + 1) / len(urls)) * 100
                logger.info(f"速度检测进度: {i + 1}/{len(urls)} ({progress:.1f}%)")
        
        valid_results = [r for r in results if r['speed'] > 0]
        logger.info(f"速度检测完成: 有效{len(valid_results)}/{len(urls)}个URL")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_processed': self.total_processed,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': (self.success_count / self.total_processed * 100) if self.total_processed > 0 else 0
        }


# 便捷函数
async def check_404_async(urls: List[str], max_concurrent: int = 20, 
                         timeout: int = 10, callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
    """异步404检测便捷函数"""
    async with AsyncNetworkChecker(max_concurrent=max_concurrent, timeout=timeout) as checker:
        return await checker.batch_check_404(urls, callback)


async def check_speed_async(urls: List[str], max_concurrent: int = 15, 
                           timeout: int = 15, callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
    """异步速度检测便捷函数"""
    async with AsyncNetworkChecker(max_concurrent=max_concurrent, timeout=timeout) as checker:
        return await checker.batch_check_speed(urls, callback)


def check_404_sync(urls: List[str], max_concurrent: int = 20, 
                   timeout: int = 10, callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
    """同步404检测兼容函数"""
    async def _check():
        return await check_404_async(urls, max_concurrent, timeout, callback)
    
    return asyncio.run(_check())


def check_speed_sync(urls: List[str], max_concurrent: int = 15, 
                    timeout: int = 15, callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
    """同步速度检测兼容函数"""
    async def _check():
        return await check_speed_async(urls, max_concurrent, timeout, callback)
    
    return asyncio.run(_check())


if __name__ == "__main__":
    # 测试代码
    async def test_async_checker():
        test_urls = [
            "http://httpbin.org/status/200",
            "http://httpbin.org/status/404",
            "http://httpbin.org/status/500",
            "http://httpbin.org/delay/2",
            "http://httpbin.org/json"
        ]
        
        print("=== 测试404检测 ===")
        async with AsyncNetworkChecker(max_concurrent=5, timeout=5) as checker:
            results = await checker.batch_check_404(test_urls)
            for result in results:
                print(f"URL: {result['url']} | 有效: {result['is_valid']} | 状态: {result['status_code']} | 错误: {result['error']}")
        
        print("\n=== 测试速度检测 ===")
        async with AsyncNetworkChecker(max_concurrent=3, timeout=10) as checker:
            results = await checker.batch_check_speed(test_urls[:3])
            for result in results:
                print(f"URL: {result['url']} | 速度: {result['speed']:.2f}MB/s | 延迟: {result['delay']}ms")
        
        print("\n=== 统计信息 ===")
        print(checker.get_stats())
    
    # 运行测试
    asyncio.run(test_async_checker())
