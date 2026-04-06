#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块 - 基于IPTV API框架
"""

import configparser
import os
from pathlib import Path


class Config:
    """配置管理类"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or "config/config.ini"
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            # 使用默认配置
            self._set_default_config()
    
    def _set_default_config(self):
        """设置默认配置"""
        self.config['Settings'] = {
            'source_file': 'resources.txt',
            'output_dir': 'output',
            'open_url_check': 'True',
            'open_video_check': 'True', 
            'open_speed_test': 'True',
            'url_check_timeout': '5',
            'video_check_timeout': '180',
            'speed_test_timeout': '10',
            'max_concurrent': '10',
            'batch_size': '50',
            'memory_threshold': '80',
            'min_speed': '204800',
            'verbose_logging': 'True',
            'show_progress': 'True',
            'open_service': 'False',
            'service_port': '8080'
        }
    
    def get(self, key: str, default=None):
        """获取配置值"""
        return self.config.get('Settings', key, fallback=default)
    
    def get_int(self, key: str, default=0):
        """获取整数配置"""
        return self.config.getint('Settings', key, fallback=default)
    
    def get_float(self, key: str, default=0.0):
        """获取浮点数配置"""
        return self.config.getfloat('Settings', key, fallback=default)
    
    def get_bool(self, key: str, default=False):
        """获取布尔配置"""
        return self.config.getboolean('Settings', key, fallback=default)
    
    @property
    def source_file(self) -> str:
        """源文件路径"""
        return self.get('source_file', 'resources.txt')
    
    @property
    def output_dir(self) -> str:
        """输出目录"""
        return self.get('output_dir', 'output')
    
    @property
    def open_url_check(self) -> bool:
        """开启URL检测"""
        return self.get_bool('open_url_check', True)
    
    @property
    def open_video_check(self) -> bool:
        """开启视频检测"""
        return self.get_bool('open_video_check', True)
    
    @property
    def open_speed_test(self) -> bool:
        """开启速度测试"""
        return self.get_bool('open_speed_test', True)
    
    @property
    def whitelist_file(self) -> str:
        """白名单文件路径"""
        return self.get('whitelist_file', 'white.txt')
    
    @property
    def url_check_timeout(self) -> int:
        """URL检测超时时间"""
        return self.get_int('url_check_timeout', 5)
    
    @property
    def video_check_timeout(self) -> int:
        """视频检测超时时间"""
        return self.get_int('video_check_timeout', 180)
    
    @property
    def speed_test_timeout(self) -> int:
        """速度测试超时时间"""
        return self.get_int('speed_test_timeout', 10)
    
    @property
    def max_concurrent(self) -> int:
        """并发检测数量"""
        return self.get_int('max_concurrent', 10)
    
    @property
    def batch_size(self) -> int:
        """批次处理大小"""
        return self.get_int('batch_size', 50)
    
    @property
    def memory_threshold(self) -> float:
        """内存使用阈值"""
        return self.get_float('memory_threshold', 80.0)
    
    @property
    def min_speed(self) -> int:
        """最小速度要求"""
        return self.get_int('min_speed', 204800)
    
    @property
    def verbose_logging(self) -> bool:
        """开启详细日志"""
        return self.get_bool('verbose_logging', True)
    
    @property
    def show_progress(self) -> bool:
        """开启进度显示"""
        return self.get_bool('show_progress', True)
    
    @property
    def open_service(self) -> bool:
        """开启结果页面服务"""
        return self.get_bool('open_service', False)
    
    @property
    def service_port(self) -> int:
        """服务端口"""
        return self.get_int('service_port', 8080)


# 全局配置实例
config = Config()
