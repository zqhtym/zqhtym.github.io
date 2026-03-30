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
    
    def __init__(self, max_concurrent: int = 10, memory_threshold: float = 80.0):
        self.max_concurrent = max_concurrent
        self.memory_threshold = memory_threshold
        self.max_memory_mb = 1500
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.process = psutil.Process()
        
        # 内存统计
        self.total_processed = 0
        self.memory_warnings = 0
        
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
        """检查内存限制"""
        memory_info = self.get_memory_info()
        
        # 记录内存使用
        logger.info(f"内存使用: RSS={memory_info['rss_mb']:.1f}MB, "
                   f"百分比={memory_info['percent']:.1f}%")
        
        # 检查是否超过阈值
        if memory_info['percent'] > self.memory_threshold:
            self.memory_warnings += 1
            logger.warning(f"内存使用过高: {memory_info['percent']:.1f}% > {self.memory_threshold}%")
            
            # 强制垃圾回收
            collected = gc.collect()
            logger.info(f"垃圾回收: 清理{collected}个对象")
            
            # 再次检查
            after_gc = self.get_memory_info()
            logger.info(f"回收后内存: {after_gc['percent']:.1f}%")
            
            return True
        
        return False
    
    async def process_item_async(self, item: Any, processor_func: Callable, 
                                **kwargs) -> Any:
        """异步处理单个项目"""
        async with self.semaphore:
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
                
                # 每处理10个项目检查一次内存
                if self.total_processed % 10 == 0:
                    self.check_memory_limit()
                
                return result
                
            except Exception as e:
                logger.error(f"处理项目失败: {e}")
                return None
    
    async def process_batch_async(self, items: List[Any], 
                                 processor_func: Callable,
                                 batch_size: int = 50,
                                 **kwargs) -> List[Any]:
        """异步批量处理项目"""
        logger.info(f"开始异步批量处理: 总数={len(items)}, 批次大小={batch_size}")
        
        results = []
        total_batches = (len(items) - 1) // batch_size + 1
        
        for batch_start in range(0, len(items), batch_size):
            batch_end = min(batch_start + batch_size, len(items))
            batch = items[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            
            logger.info(f"处理批次 {batch_num}/{total_batches} (数量: {len(batch)})")
            
            # 创建任务列表
            tasks = [
                self.process_item_async(item, processor_func, **kwargs)
                for item in batch
            ]
            
            # 等待所有任务完成
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"批次处理异常: {result}")
                elif result is not None:
                    results.append(result)
            
            # 批次间内存检查
            memory_info = self.get_memory_info()
            if memory_info['percent'] > 75:
                logger.warning("批次间内存过高，暂停2秒")
                await asyncio.sleep(2)
                gc.collect()
            
            # 每批次后短暂暂停
            if batch_num < total_batches:
                await asyncio.sleep(0.1)
        
        logger.info(f"异步批量处理完成: 处理{len(results)}个结果")
        return results
    
    async def process_with_memory_control(self, items: List[Any],
                                        processor_func: Callable,
                                        max_memory_mb: Optional[int] = None,
                                        **kwargs) -> List[Any]:
        """带内存控制的处理"""
        if max_memory_mb:
            self.max_memory_mb = max_memory_mb
        
        logger.info(f"开始内存控制处理: 最大并发={self.max_concurrent}, "
                   f"内存阈值={self.memory_threshold}%")
        
        start_time = time.time()
        
        try:
            # 深拷贝避免内存污染
            items_copy = copy.deepcopy(items)
            
            # 异步处理
            results = await self.process_batch_async(
                items_copy, processor_func, **kwargs
            )
            
            # 清理拷贝的数据
            del items_copy
            gc.collect()
            
            end_time = time.time()
            logger.info(f"处理完成: 耗时{end_time - start_time:.2f}秒, "
                       f"结果{len(results)}个, 内存警告{self.memory_warnings}次")
            
            return results
            
        except Exception as e:
            logger.error(f"内存控制处理失败: {e}")
            raise
        finally:
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
