#!/usr/bin/env python3

# video_check_worker.py - 独立的画面检测进程



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

    """全局配置类"""

    # 请求头

    HEADERS = {

        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    }



    # 超时配置

    TIMEOUT = {

        'remote_fetch': 10,

        '404_check': 3,

        'speed_test': 5,

        'stream_read': 5,

        'video_check': 15,  # 画面检测超时（秒）

        'video_total_timeout': 180  # 画面检测总超时（3分钟=180秒）

    }



    # 画面检测配置

    VIDEO_CHECK = {

        'frame_interval': 2,  # 每隔2秒取一帧

        'min_diff': 5000,     # 帧差异阈值（低于此值视为画面无变化）

        'min_width': 320,     # 最小有效宽度

        'min_height': 240,    # 最小有效高度

        'audio_check': True   # 是否检测音频

    }





# 全局变量用于超时控制

timeout_flag = False





def timeout_handler():

    """超时回调函数"""

    global timeout_flag

    timeout_flag = True





def check_ffmpeg():
    """检查FFmpeg是否可用"""
    
    # 首先检查系统PATH中是否有ffmpeg
    if shutil.which('ffmpeg'):
        return True
    
    # GitHub Actions环境检查
    if os.environ.get('GITHUB_ACTIONS'):
        # 在GitHub Actions中，ffmpeg应该已经通过apt安装
        # 检查常见的安装位置
        github_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/ffmpeg/bin/ffmpeg'
        ]
        
        for path in github_paths:
            if os.path.exists(path):
                os.environ['PATH'] += os.pathsep + os.path.dirname(path)
                return True
        
        print(f"[GitHub Actions] FFmpeg未找到，请确保已安装ffmpeg")
        return False
    
    # 本地Windows环境检查
    if sys.platform.startswith('win'):
        # 尝试常见Windows路径
        ffmpeg_paths = [
            r'H:\11 tool\装机\视频\哔哩下载姬（downkyi）-27-1.3.4\ffmpeg.exe',
            r'C:\Users\Administrator\AppData\Roaming\anythingllm-desktop\storage\engines\ffmpeg\windows-x64\ffmpeg.exe',
            r'C:\Program Files\iGameCenter\SAVIConverter\tools\ffmpeg.exe',
            r'C:\Users\Administrator\AppData\Local\Programs\icat\resources\bin\ffmpeg\ffmpeg.exe',
            r'C:\ffmpeg\ffmpeg.exe',  # 常见安装位置
            r'C:\ffmpeg\bin\ffmpeg.exe'  # 另一种常见安装位置
        ]
        
        for path in ffmpeg_paths:
            if os.path.exists(path):
                os.environ['PATH'] += os.pathsep + os.path.dirname(path)
                print(f"[FFmpeg] 找到FFmpeg: {path}")
                return True
    
    # Linux/Mac环境检查
    else:
        # 尝试常见Unix路径
        unix_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/homebrew/bin/ffmpeg',  # Mac Homebrew
            '/opt/ffmpeg/bin/ffmpeg'
        ]
        
        for path in unix_paths:
            if os.path.exists(path):
                os.environ['PATH'] += os.pathsep + os.path.dirname(path)
                print(f"[FFmpeg] 找到FFmpeg: {path}")
                return True
    
    print(f"[FFmpeg] 未找到FFmpeg，画面检测功能将受限")
    return False





def check_video_changes(url):

    """

    检测15秒内画面是否变化（新增404前置检测+无效URL容错）

    改写返回值：返回字典包含详细检测结果

    返回格式：

    {

        'success': bool,       # 检测是否成功执行（非结果是否变化）

        'changing': bool,      # 画面是否有变化

        'reason': str,         # 失败原因/备注信息

        'frame_info': {        # 帧信息（成功时有效）

            'total_read': int, # 总读取帧数

            'valid_frames': int,# 有效对比帧数

            'avg_diff': float   # 平均帧差异值

        }

    }

    """

    global timeout_flag

    timeout_flag = False  # 重置超时标记



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



    # 1. 设置3分钟超时定时器

    timer = threading.Timer(Config.TIMEOUT['video_total_timeout'], timeout_handler)

    timer.start()



    try:

        # 前置步骤1：检测URL是否存在（避免404导致帧数为0）

        try:

            req = Request(url, headers=Config.HEADERS, method='HEAD')

            with urlopen(req, timeout=3):

                url_valid = True

        except HTTPError as e:

            if e.code == 404:

                reason = f"URL: {url} | 错误: 404 Not Found（链接无效）"

                print(f"[调试] 画面变化检测失败 | {reason}")

                result['reason'] = reason

                return result

            url_valid = True  # 非404错误（如500）仍尝试读取

        except (URLError, TimeoutError):

            reason = f"URL: {url} | 错误: 无法连接（网络超时/链接不可达）"

            print(f"[调试] 画面变化检测失败 | {reason}")

            result['reason'] = reason

            return result



        if not url_valid:

            result['reason'] = f"URL: {url} | 错误: URL验证失败"

            return result



        # 前置步骤2：判断是否为ts片段（避免单一片段无法播放）

        url_lower = url.lower()

        if url_lower.endswith('.ts'):

            reason = f"URL: {url} | 提示：TS片段需通过m3u8索引播放，单独无法解析画面"

            print(f"[调试] 检测到TS单一片段 | {reason}")

            result['reason'] = reason

            return result



        # 尝试读取视频流

        ffmpeg_url = f'ffmpeg://{url}' if check_ffmpeg() else url

        cap = cv2.VideoCapture(ffmpeg_url)



        # 设置超时和缓冲参数

        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # 5秒打开超时

        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)   # 5秒读取超时



        if not cap.isOpened():

            # 二次尝试：直接用OpenCV读取（兼容无FFmpeg场景）

            cap = cv2.VideoCapture(url)

            if not cap.isOpened():

                reason = f"URL: {url} | 错误: 无法打开视频流（格式不支持/链接无效）"

                print(f"[调试] 画面变化检测失败 | {reason}")

                result['reason'] = reason

                cap.release()

                return result



        # 3. 读取帧并检测变化（带超时检查）

        frames = []

        start_time = time.time()

        last_frame_time = start_time

        frame_read_count = 0  # 统计成功读取的帧数



        while time.time() - start_time < Config.TIMEOUT['video_check']:

            # 检查是否超时（3分钟）

            if timeout_flag:

                reason = f"URL: {url} | 原因: 超过3分钟强制终止"

                print(f"[调试] 画面检测超时 | {reason}")

                result['reason'] = reason

                cap.release()

                return result



            ret, frame = cap.read()

            if not ret:

                break  # 无更多帧或读取失败



            frame_read_count += 1

            current_time = time.time()

            # 每隔指定时间取一帧（减少计算量）

            if current_time - last_frame_time >= Config.VIDEO_CHECK['frame_interval']:

                # 转为灰度图并缩小

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                gray = cv2.resize(gray, (320, 240))

                frames.append(gray)

                last_frame_time = current_time



            # 最多取5帧（足够判断变化，避免耗时过长）

            if len(frames) >= 5:

                break



        cap.release()



        # 异常情况处理

        if frame_read_count == 0:

            reason = f"URL: {url} | 错误: 未读取到任何视频帧（可能是无效流/格式不支持）"

            print(f"[调试] 画面变化检测失败 | {reason}")

            result['reason'] = reason

            return result



        if len(frames) < 2:

            reason = f"URL: {url} | 错误: 有效帧数不足（共读取{frame_read_count}帧，需至少2帧对比）"

            print(f"[调试] 画面变化检测失败 | {reason}")

            result['reason'] = reason

            return result



        # 计算相邻帧差异

        total_diff = 0

        for i in range(1, len(frames)):

            diff = cv2.absdiff(frames[i-1], frames[i])

            non_zero = np.count_nonzero(diff)

            total_diff += non_zero



        avg_diff = total_diff / (len(frames) - 1)

        is_changing = avg_diff > Config.VIDEO_CHECK['min_diff']



        # 填充成功结果

        result['success'] = True

        result['changing'] = is_changing

        result['reason'] = "检测成功"

        result['frame_info'] = {

            'total_read': frame_read_count,

            'valid_frames': len(frames),

            'avg_diff': round(avg_diff, 2)

        }



        print(f"[调试] 画面变化检测成功 | URL: {url} | 读取帧数: {frame_read_count} | 有效对比帧数: {len(frames)} | 平均帧差异: {avg_diff:.0f} | 变化: {is_changing}")

        return result



    except Exception as e:

        # 异常时检查是否超时

        if timeout_flag:

            reason = f"URL: {url} | 原因: 超过3分钟强制终止"

            print(f"[调试] 画面检测超时 | {reason}")

        else:

            reason = f"URL: {url} | 错误: {str(e)}"

            print(f"[调试] 画面变化检测异常 | {reason}")

            import traceback

            traceback.print_exc()

        result['reason'] = reason

        return result



    finally:

        # 停止定时器（避免内存泄漏）

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

    result = check_video_changes(url)

    # 输出JSON格式结果，方便外部程序解析

    print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0)