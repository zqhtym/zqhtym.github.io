#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
类型定义模块 - 基于IPTV API框架
"""

from typing import TypedDict, List, Dict, Any, Optional


class ChannelData(TypedDict):
    """频道数据类型"""
    url: str
    date: Optional[str]
    resolution: Optional[str]
    origin: str
    ipv_type: Optional[str]


class CategoryChannelData(Dict[str, Dict[str, List[ChannelData]]]):
    """分类频道数据类型"""
    pass


class CheckResult(TypedDict):
    """检测结果类型"""
    url: str
    is_valid: bool
    error: Optional[str]
    response_time: Optional[float]


class SpeedResult(TypedDict):
    """速度测试结果类型"""
    url: str
    speed: float  # MB/s
    delay: Optional[float]  # ms
    error: Optional[str]


class VideoResult(TypedDict):
    """视频检测结果类型"""
    url: str
    has_video: bool
    has_audio: bool
    video_changing: bool
    error: Optional[str]


class ProcessStats(TypedDict):
    """处理统计类型"""
    total_processed: int
    success_count: int
    error_count: int
    cache_hits: int
    memory_warnings: int
