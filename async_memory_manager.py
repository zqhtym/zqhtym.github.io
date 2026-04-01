#!/usr/bin/env python3
# async_memory_manager.py - 基于IPTV API模式的异步内存管理

import asyncio
import copy
import gc
import time
import psutil
from typing import List, Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncMemoryManager:
    """基于IPTV API模式的异步内存管理器"""
    
    def __init__(self, max_concurrent: int = 10, memory_threshold: float = 60.0):
        self.max_concurrent = max_concurrent
        self.memory_threshold = memory_threshold
        self.max_memory_mb = 800
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.process = psutil.Process()
        
        # 内存统计
        self.total_processed = 0
        self.memory_warnings = 0
        
        # IPTV API风格的垃圾回收配置
        gc.set_threshold(200, 2, 2)  # 更频繁的GC
        
        # 缓存机制（参考IPTV API）
        self.cache = {}
        self.cache_hits = 0
        
    def get_memory_info(self) -> dict:
        """获取内存信息"""
        try:
            memory_info = self.process.memory_info()
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': self.process.memory_percent()
            }
        except Exception as e:
            logger.error(f"获取内存信息失败: {e}")
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0}
    
    def check_memory_limit(self) -> bool:
        """检查内存限制 - 基于IPTV API模式"""
        memory_info = self.get_memory_info()
        
        # 记录内存使用
        logger.info(f"内存使用: RSS={memory_info['rss_mb']:.1f}MB, "
                   f"百分比={memory_info['percent']:.1f}%")
        
        # IPTV API风格的内存检查
        if memory_info['rss_mb'] > self.max_memory_mb or memory_info['percent'] > self.memory_threshold:
            self.memory_warnings += 1
            logger.warning(f"内存使用过高: RSS={memory_info['rss_mb']:.1f}MB > {self.max_memory_mb}MB, "
                         f"百分比={memory_info['percent']:.1f}% > {self.memory_threshold}%")
            
            # IPTV API风格的垃圾回收：多轮清理
            for i in range(3):
                collected = gc.collect()
                logger.info(f"IPTV风格垃圾回收第{i+1}轮: 清理{collected}个对象")
                time.sleep(0.1)
            
            # 清理缓存（参考IPTV API）
            if len(self.cache) > 1000:  # 缓存过大时清理
                self.cache.clear()
                logger.info("清理内存缓存")
            
            # 再次检查
            after_gc = self.get_memory_info()
            logger.info(f"回收后内存: RSS={after_gc['rss_mb']:.1f}MB, "
                       f"百分比={after_gc['percent']:.1f}%")
            
            # 如果仍然过高，返回True表示需要暂停
            if after_gc['rss_mb'] > self.max_memory_mb * 0.9 or after_gc['percent'] > self.memory_threshold * 0.9:
                return True
            
        return False
    
    def get_cache_key(self, item: Any) -> str:
        """生成缓存键（参考IPTV API）"""
        try:
            # 基于URL生成缓存键
            if hasattr(item, 'url'):
                return str(hash(item.url))
            return str(hash(str(item)))
        except:
            return str(time.time())
    
    def get_cached_result(self, item: Any) -> Any:
        """获取缓存结果（参考IPTV API）"""
        cache_key = self.get_cache_key(item)
        if cache_key in self.cache:
            self.cache_hits += 1
            logger.debug(f"缓存命中: {cache_key}")
            return copy.deepcopy(self.cache[cache_key])
        return None
    
    def set_cached_result(self, item: Any, result: Any) -> None:
        """设置缓存结果（参考IPTV API）"""
        cache_key = self.get_cache_key(item)
        # 限制缓存大小
        if len(self.cache) < 1000:
            self.cache[cache_key] = copy.deepcopy(result)
    
    async def process_item_async(self, item: Any, processor_func: Callable, 
                                **kwargs) -> Any:
        """异步处理单个项目 - 基于IPTV API模式"""
        async with self.semaphore:
            # IPTV API风格：先检查缓存
            cached_result = self.get_cached_result(item)
            if cached_result is not None:
                return cached_result
            
            # 检查内存
            self.check_memory_limit()
            
            try:
                # 如果处理器是同步函数，使用线程池
                if not asyncio.iscoroutinefunction(processor_func):
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        self.executor, processor_func, item, **kwargs
                    )
                else:
                    # 如果是异步函数，直接调用
                    result = await processor_func(item, **kwargs)
                
                self.total_processed += 1
                
                # IPTV API风格：缓存结果
                self.set_cached_result(item, result)
                
                # 每处理5个项目检查一次内存（IPTV API风格）
                if self.total_processed % 5 == 0:
                    self.check_memory_limit()
                
                return result
                
            except Exception as e:
                logger.error(f"处理项目失败: {e}")
                return None
    
    async def process_batch_async(self, items: List[Any], 
                                 processor_func: Callable,
                                 batch_size: int = 50,
                                 **kwargs) -> List[Any]:
        """异步批量处理项目 - 基于IPTV API模式"""
        logger.info(f"开始IPTV风格批量处理: 总数={len(items)}, 批次大小={batch_size}")
        
        # IPTV API风格：深拷贝避免内存污染
        items_copy = copy.deepcopy(items)
        
        results = []
        total_batches = (len(items_copy) - 1) // batch_size + 1
        
        for batch_start in range(0, len(items_copy), batch_size):
            batch_end = min(batch_start + batch_size, len(items_copy))
            batch = items_copy[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            
            logger.info(f"处理批次 {batch_num}/{total_batches} (数量: {len(batch)})")
            
            # IPTV API风格：创建并发任务
            tasks = [
                self.process_item_async(item, processor_func, **kwargs)
                for item in batch
            ]
            
            # IPTV API风格：使用asyncio.gather并发执行
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"批次处理异常: {result}")
                elif result is not None:
                    results.append(result)
            
            # IPTV API风格：批次间内存检查
            memory_info = self.get_memory_info()
            if memory_info['percent'] > 50:  # 更严格的阈值
                logger.warning(f"IPTV风格批次间内存过高，暂停3秒: {memory_info['percent']:.1f}%")
                await asyncio.sleep(3)
                
                # IPTV API风格：强制垃圾回收
                for i in range(2):
                    collected = gc.collect()
                    logger.info(f"IPTV风格暂停后垃圾回收第{i+1}轮: 清理{collected}个对象")
                    await asyncio.sleep(0.3)
                
                # 检查是否需要跳过剩余批次
                final_memory = self.get_memory_info()
                if final_memory['percent'] > 70:
                    logger.error(f"IPTV风格内存仍然过高: {final_memory['percent']:.1f}%，终止处理")
                    break
            
            # IPTV API风格：清理批次数据
            del batch
            gc.collect()
            
            # 每批次后短暂暂停
            if batch_num < total_batches:
                await asyncio.sleep(0.2)
        
        # 清理拷贝数据
        del items_copy
        gc.collect()
        
        logger.info(f"IPTV风格批量处理完成: 处理{len(results)}个结果, 缓存命中{self.cache_hits}次")
        return results
    
    async def process_with_memory_control(self, items: List[Any],
                                        processor_func: Callable,
                                        batch_size: int = 50,
                                        max_memory_mb: int = 800) -> List[Any]:
        """基于IPTV API模式的内存控制处理"""
        self.max_memory_mb = max_memory_mb
        
        # IPTV API风格：初始垃圾回收
        gc.collect()
        
        try:
            return await self.process_batch_async(items, processor_func, batch_size)
        finally:
            # IPTV API风格：清理资源
            await self.cleanup()
    
    async def cleanup(self):
        """清理资源 - 基于IPTV API模式"""
        # 清理缓存
        self.cache.clear()
        
        # 关闭线程池
        if self.executor:
            self.executor.shutdown(wait=True)
        
        # 最终垃圾回收
        for i in range(3):
            collected = gc.collect()
            logger.info(f"清理垃圾回收第{i+1}轮: 清理{collected}个对象")
            time.sleep(0.1)
            # 确保清理
            gc.collect()
    
    def get_stats(self) -> dict:
        """获取处理统计"""
        memory_info = self.get_memory_info()
        return {
            'total_processed': self.total_processed,
            'memory_warnings': self.memory_warnings,
            'current_memory_mb': memory_info['rss_mb'],
            'current_memory_percent': memory_info['percent'],
            'max_concurrent': self.max_concurrent
        }
    
    def cleanup(self):
        """清理资源"""
        if self.executor:
            self.executor.shutdown(wait=True)
        gc.collect()
        logger.info("异步内存管理器已清理")


# 全局实例
async_memory_manager = AsyncMemoryManager()


# 便捷函数
async def process_items_async(items: List[Any], processor_func: Callable, 
                            max_concurrent: int = 10, **kwargs) -> List[Any]:
    """异步处理项目的便捷函数"""
    manager = AsyncMemoryManager(max_concurrent=max_concurrent)
    try:
        return await manager.process_with_memory_control(items, processor_func, **kwargs)
    finally:
        manager.cleanup()


def process_items_sync(items: List[Any], processor_func: Callable,
                     max_concurrent: int = 10, **kwargs) -> List[Any]:
    """同步处理项目的便捷函数（兼容性函数）"""
    async def _process():
        return await process_items_async(items, processor_func, max_concurrent, **kwargs)
    
    return asyncio.run(_process())


# 装饰器
def async_memory_safe(max_concurrent: int = 10):
    """异步内存安全装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = AsyncMemoryManager(max_concurrent=max_concurrent)
            try:
                # 如果函数是异步的
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    # 同步函数转换为异步
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(manager.executor, func, *args, **kwargs)
            finally:
                manager.cleanup()
        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试代码
    async def test_processor(item):
        """测试处理器"""
        await asyncio.sleep(0.1)  # 模拟处理时间
        return item * 2
    
    async def test_async_manager():
        """测试异步管理器"""
        test_items = list(range(100))
        
        # 测试异步处理
        results = await process_items_async(
            test_items, test_processor, max_concurrent=5
        )
        
        print(f"测试结果: {len(results)}个项目")
        print(f"前10个结果: {results[:10]}")
        
        # 获取统计
        stats = async_memory_manager.get_stats()
        print(f"处理统计: {stats}")
    
    # 运行测试
    asyncio.run(test_async_manager())
