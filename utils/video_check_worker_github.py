#!/usr/bin/env python3
# video_check_worker_github.py - 针对GitHub Actions外网环境优化的画面检测

import os
import sys
import json
import cv2
import time
import shutil
import threading
import numpy as np
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ======================== 全局配置模块 ========================
class Config:
    """全局配置类 - GitHub Actions优化版"""
    # 请求头
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # 超时配置 - 针对外网环境优化
    TIMEOUT = {
        'remote_fetch': 15,     # 增加远程获取超时
        '404_check': 10,        # 增加404检测超时
        'speed_test': 20,       # 增加速度测试超时
        'stream_read': 10,      # 增加流读取超时
        'video_check': 20,      # 增加画面检测超时
        'video_total_timeout': 240  # 增加总超时到4分钟
    }

    # 画面检测配置 - 外网环境优化
    VIDEO_CHECK = {
        'frame_interval': 2,    # 降低采样频率，减少网络压力
        'min_diff': 500,        # 进一步降低阈值，适应网络波动
        'min_width': 320,       # 最小有效宽度
        'min_height': 240,      # 最小有效高度
        'audio_check': False,   # 关闭音频检测，减少复杂性
        'min_frames': 2,        # 减少最少帧数要求
        'max_frames': 5,        # 减少最大帧数，降低网络负载
        'retry_count': 2,       # 添加重试次数
        'network_tolerance': 0.3 # 网络容错率
    }


# 全局变量用于超时控制
timeout_flag = False


def timeout_handler():
    """超时回调函数"""
    global timeout_flag
    timeout_flag = True


def check_ffmpeg():
    """检查FFmpeg是否可用"""
    if shutil.which('ffmpeg'):
        return True
    # GitHub Actions环境FFmpeg路径
    ffmpeg_paths = [
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/opt/ffmpeg/bin/ffmpeg'
    ]
    for path in ffmpeg_paths:
        if os.path.exists(path):
            return True
    return False


def simulate_network_delay():
    """模拟网络延迟，用于测试"""
    if os.environ.get('SIMULATE_NETWORK_DELAY'):
        time.sleep(float(os.environ.get('SIMULATE_NETWORK_DELAY', '0.1')))


def check_video_changes_github(url):
    """
    针对GitHub Actions外网环境的画面检测
    优化策略：
    1. 增加超时时间
    2. 降低检测要求
    3. 添加重试机制
    4. 网络容错处理
    """
    global timeout_flag
    timeout_flag = False

    # 初始化返回结果
    result = {
        'success': False,
        'changing': False,
        'reason': '',
        'frame_info': {
            'total_read': 0,
            'valid_frames': 0,
            'avg_diff': 0.0
        }
    }

    # 设置4分钟超时定时器
    timer = threading.Timer(Config.TIMEOUT['video_total_timeout'], timeout_handler)
    timer.start()

    try:
        # 模拟网络延迟（仅用于测试）
        simulate_network_delay()

        # 前置步骤1：检测URL是否存在（增加重试）
        url_valid = False
        for attempt in range(Config.VIDEO_CHECK['retry_count'] + 1):
            try:
                req = Request(url, headers=Config.HEADERS, method='HEAD')
                with urlopen(req, timeout=Config.TIMEOUT['404_check']):
                    url_valid = True
                    break
            except HTTPError as e:
                if e.code == 404:
                    reason = f"URL: {url} | 错误: 404 Not Found（链接无效）"
                    print(f"[调试] 画面变化检测失败 | {reason}")
                    result['reason'] = reason
                    return result
                # 非404错误继续重试
                if attempt < Config.VIDEO_CHECK['retry_count']:
                    print(f"[调试] 网络错误，重试 {attempt + 1}/{Config.VIDEO_CHECK['retry_count']}")
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                else:
                    url_valid = True  # 最后一次尝试仍继续
            except (URLError, TimeoutError) as e:
                if attempt < Config.VIDEO_CHECK['retry_count']:
                    print(f"[调试] 网络连接错误，重试 {attempt + 1}/{Config.VIDEO_CHECK['retry_count']}: {e}")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    reason = f"URL: {url} | 错误: 网络连接失败（外网环境限制）"
                    print(f"[调试] 画面变化检测失败 | {reason}")
                    result['reason'] = reason
                    return result

        if not url_valid:
            result['reason'] = f"URL: {url} | 错误: URL验证失败"
            return result

        # 前置步骤2：判断是否为ts片段
        url_lower = url.lower()
        if url_lower.endswith('.ts'):
            reason = f"URL: {url} | 提示：TS片段需通过m3u8索引播放"
            print(f"[调试] 检测到TS单一片段 | {reason}")
            result['reason'] = reason
            return result

        # 尝试读取视频流（增加重试机制）
        cap = None
        for attempt in range(Config.VIDEO_CHECK['retry_count'] + 1):
            try:
                ffmpeg_url = f'ffmpeg://{url}' if check_ffmpeg() else url
                cap = cv2.VideoCapture(ffmpeg_url)

                # 设置超时参数（外网环境增加）
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)  # 10秒打开超时
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)   # 10秒读取超时

                if cap.isOpened():
                    break
                else:
                    cap.release()
                    cap = None
                    
            except Exception as e:
                if cap:
                    cap.release()
                    cap = None
                if attempt < Config.VIDEO_CHECK['retry_count']:
                    print(f"[调试] 视频流打开失败，重试 {attempt + 1}/{Config.VIDEO_CHECK['retry_count']}: {e}")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    reason = f"URL: {url} | 错误: 无法打开视频流（外网环境限制）"
                    print(f"[调试] 画面变化检测失败 | {reason}")
                    result['reason'] = reason
                    return result

        if not cap or not cap.isOpened():
            reason = f"URL: {url} | 错误: 无法打开视频流（格式不支持/外网限制）"
            print(f"[调试] 画面变化检测失败 | {reason}")
            result['reason'] = reason
            if cap:
                cap.release()
            return result

        # 读取帧并检测变化
        frames = []
        start_time = time.time()
        last_frame_time = start_time
        frame_read_count = 0
        failed_reads = 0  # 记录连续读取失败次数

        while time.time() - start_time < Config.TIMEOUT['video_check']:
            # 检查是否超时
            if timeout_flag:
                reason = f"URL: {url} | 原因: 检测超时（外网环境）"
                print(f"[调试] 画面检测超时 | {reason}")
                result['reason'] = reason
                cap.release()
                return result

            ret, frame = cap.read()
            if not ret:
                failed_reads += 1
                # 外网环境允许一定的读取失败
                if failed_reads > 10:  # 连续失败10次则退出
                    break
                time.sleep(0.1)  # 短暂等待
                continue

            failed_reads = 0  # 重置失败计数
            frame_read_count += 1
            current_time = time.time()
            
            # 采样帧（降低频率）
            if current_time - last_frame_time >= Config.VIDEO_CHECK['frame_interval']:
                try:
                    # 转为灰度图并缩小
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray = cv2.resize(gray, (320, 240))
                    frames.append(gray)
                    last_frame_time = current_time
                except Exception as e:
                    print(f"[调试] 帧处理失败，跳过: {e}")
                    continue

            # 达到最大帧数则停止
            if len(frames) >= Config.VIDEO_CHECK['max_frames']:
                break

        cap.release()

        # 检查是否读取到有效帧
        if frame_read_count == 0:
            reason = f"URL: {url} | 错误: 未读取到任何视频帧（外网网络问题）"
            print(f"[调试] 画面变化检测失败 | {reason}")
            result['reason'] = reason
            return result

        if len(frames) < Config.VIDEO_CHECK['min_frames']:
            reason = f"URL: {url} | 错误: 有效帧数不足（共读取{frame_read_count}帧，有效{len(frames)}帧）"
            print(f"[调试] 画面变化检测失败 | {reason}")
            result['reason'] = reason
            return result

        # 计算相邻帧差异
        total_diff = 0
        valid_diffs = 0
        for i in range(1, len(frames)):
            try:
                diff = cv2.absdiff(frames[i-1], frames[i])
                non_zero = np.count_nonzero(diff)
                total_diff += non_zero
                valid_diffs += 1
            except Exception as e:
                print(f"[调试] 帧差异计算失败，跳过: {e}")
                continue

        if valid_diffs == 0:
            reason = f"URL: {url} | 错误: 无法计算帧差异"
            print(f"[调试] 画面变化检测失败 | {reason}")
            result['reason'] = reason
            return result

        avg_diff = total_diff / valid_diffs
        
        # 外网环境降低判断标准
        is_changing = avg_diff > Config.VIDEO_CHECK['min_diff']

        # 填充成功结果
        result['success'] = True
        result['changing'] = is_changing
        result['reason'] = "检测成功（外网环境）"
        result['frame_info'] = {
            'total_read': frame_read_count,
            'valid_frames': len(frames),
            'avg_diff': round(avg_diff, 2)
        }

        print(f"[调试] 画面变化检测成功（外网） | URL: {url} | 读取帧数: {frame_read_count} | 有效对比帧数: {len(frames)} | 平均帧差异: {avg_diff:.0f} | 变化: {is_changing}")
        return result

    except Exception as e:
        if timeout_flag:
            reason = f"URL: {url} | 原因: 检测超时（外网环境）"
            print(f"[调试] 画面检测超时 | {reason}")
        else:
            reason = f"URL: {url} | 错误: {str(e)}"
            print(f"[调试] 画面变化检测异常（外网） | {reason}")
        result['reason'] = reason
        return result

    finally:
        timer.cancel()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        output = {
            'success': False,
            'reason': 'invalid_args',
            'changing': False,
            'frame_info': {
                'total_read': 0,
                'valid_frames': 0,
                'avg_diff': 0.0
            }
        }
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(1)
    
    url = sys.argv[1]
    result = check_video_changes_github(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)
