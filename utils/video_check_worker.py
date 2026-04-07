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

import subprocess

from urllib.request import Request, urlopen

from urllib.error import HTTPError, URLError

try:
    from pymediainfo import MediaInfo
except ImportError:
    MediaInfo = None





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

        'frame_interval': 3,  # 每隔3秒取一帧（降低采样频率）

        'min_diff': 3000,     # 帧差异阈值（进一步降低阈值）

        'min_width': 240,     # 最小有效宽度（降低要求）

        'min_height': 180,    # 最小有效高度（降低要求）

        'audio_check': True    # 开启音频检测

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
            r'C:\ffmpeg\bin\ffmpeg.exe',  # 另一种常见安装位置
            r'ffmpeg.exe',  # 项目根目录
            r'.\ffmpeg.exe'  # 当前目录
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





def analyze_media_info_with_mediainfo(url):
    """
    使用MediaInfo检测音视频轨道
    参考url-check_v-pro.py的实现
    """
    if not MediaInfo:
        return False, False
    
    def run_with_timeout(func, timeout_seconds):
        """带超时的执行函数"""
        result_container = [None]
        exception_container = [None]
        
        def target():
            try:
                result_container[0] = func()
            except Exception as e:
                exception_container[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout_seconds)
        
        if thread.is_alive():
            return None, TimeoutError("MediaInfo分析超时")
        
        if exception_container[0]:
            return None, exception_container[0]
        
        return result_container[0], None
    
    def analyze_without_timeout():
        """无超时的实际分析函数"""
        media_info = MediaInfo.parse(url)
        
        has_video = False
        has_audio = False
        
        # 兼容不同版本的MediaInfo返回格式
        if hasattr(media_info, 'tracks'):
            tracks = media_info.tracks
        else:
            tracks = media_info
        
        for track in tracks:
            # 兼容不同版本的属性名
            track_type = getattr(track, 'track_type', getattr(track, 'type', ''))
            
            if track_type == 'Video':
                width = getattr(track, 'width', 0)
                height = getattr(track, 'height', 0)
                if width >= Config.VIDEO_CHECK['min_width'] and height >= Config.VIDEO_CHECK['min_height']:
                    has_video = True
            elif track_type == 'Audio':
                has_audio = True
        
        return has_video, has_audio
    
    try:
        # 使用30秒超时执行MediaInfo分析
        result, error = run_with_timeout(analyze_without_timeout, 30)
        
        if error:
            if isinstance(error, TimeoutError):
                print(f"[调试] 媒体信息分析超时 | URL: {url} | 错误: {error}")
            else:
                print(f"[调试] 媒体信息分析失败 | URL: {url} | 错误: {error}")
            # 降级方案：使用FFmpeg检测（如果可用）
            if check_ffmpeg():
                return analyze_media_info_with_ffmpeg(url)
            return False, False
        
        return result
    
    except Exception as e:
        print(f"[调试] 媒体信息分析异常 | URL: {url} | 错误: {e}")
        # 降级方案：使用FFmpeg检测（如果可用）
        if check_ffmpeg():
            return analyze_media_info_with_ffmpeg(url)
        return False, False


def analyze_media_info_with_ffmpeg(url):
    """
    降级方案：使用FFmpeg检测音视频轨道
    参考url-check_v-pro.py的实现
    """
    try:
        # 检测视频轨道（设置较短超时）
        cmd = [
            'ffmpeg', '-i', url,
            '-hide_banner', '-nostats', '-v', 'error',
            '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'default=noprint_wrappers=1:nokey=1'
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15  # 15秒超时
            )
        except subprocess.TimeoutExpired:
            print(f"[调试] FFmpeg视频检测超时 | URL: {url} | 超时时间: 15秒")
            return False, False
        
        has_video = False
        output = result.stdout.strip()
        if output and len(output.split()) >= 2:
            try:
                width, height = output.split()
                if int(width) >= Config.VIDEO_CHECK['min_width'] and int(height) >= Config.VIDEO_CHECK['min_height']:
                    has_video = True
            except ValueError:
                print(f"[调试] FFmpeg视频输出解析失败 | URL: {url} | 输出: {output}")
        
        # 检测音频轨道（设置较短超时）
        cmd_audio = [
            'ffmpeg', '-i', url,
            '-hide_banner', '-nostats', '-v', 'error',
            '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1'
        ]
        try:
            result_audio = subprocess.run(
                cmd_audio,
                capture_output=True,
                text=True,
                timeout=15  # 15秒超时
            )
        except subprocess.TimeoutExpired:
            print(f"[调试] FFmpeg音频检测超时 | URL: {url} | 超时时间: 15秒")
            return has_video, False
        
        has_audio = False
        output_audio = result_audio.stdout.strip()
        if output_audio:
            has_audio = True
        
        return has_video, has_audio
    
    except Exception as e:
        print(f"[调试] FFmpeg检测异常 | URL: {url} | 错误: {e}")
        return False, False


def check_video_changes(url):
    """
    检测15秒内画面是否变化（参考url-check_v-pro.py实现）
    优先使用MediaInfo检测，失败后使用画面变化检测
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

    # 1. 首先尝试MediaInfo检测（更准确）
    print(f"[调试] 开始MediaInfo检测 | URL: {url}")
    has_video, has_audio = analyze_media_info_with_mediainfo(url)
    
    if has_video and has_audio:
        result['success'] = True
        result['changing'] = True  # 有视频和音频就认为有效
        result['reason'] = "MediaInfo检测成功：有视频和音频轨道"
        result['frame_info'] = {
            'total_read': 1,
            'valid_frames': 1,
            'avg_diff': 0.0
        }
        print(f"[调试] MediaInfo检测成功 | URL: {url} | 有视频: {has_video} | 有音频: {has_audio}")
        
        # 输出JSON格式结果，方便外部程序解析
        output_result = {
            'has_video': has_video,
            'has_audio': has_audio,
            'video_changing': True,
            'error': None
        }
        print(json.dumps(output_result, ensure_ascii=False))
        return result
    
    # 2. 如果MediaInfo失败，回退到画面变化检测
    print(f"[调试] MediaInfo检测失败，回退到画面变化检测 | URL: {url}")
    
    # 3. 设置3分钟超时定时器

    timer = threading.Timer(Config.TIMEOUT['video_total_timeout'], timeout_handler)

    timer.start()

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

        # 在画面变化检测前，先检测音频
        has_audio_detected = False
        try:
            # 使用FFmpeg检测音频轨道
            cmd_audio = [
                'ffmpeg', '-i', url,
                '-hide_banner', '-nostats', '-v', 'error',
                '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1'
            ]
            result_audio = subprocess.run(
                cmd_audio,
                capture_output=True,
                text=True,
                timeout=15  # 15秒超时
            )
            output_audio = result_audio.stdout.strip()
            if output_audio:
                has_audio_detected = True
                print(f"[调试] 音频检测成功 | URL: {url}")
        except subprocess.TimeoutExpired:
            print(f"[调试] 音频检测超时 | URL: {url}")
        except Exception as e:
            print(f"[调试] 音频检测异常 | URL: {url} | 错误: {e}")

        # 输出JSON格式结果，方便外部程序解析
        output_result = {
            'has_video': True,
            'has_audio': has_audio_detected,  # 使用实际检测结果
            'video_changing': is_changing,
            'error': None
        }

        print(json.dumps(output_result, ensure_ascii=False))

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

    if not result['success']:
        output_result = {
            'has_video': False,
            'has_audio': False,
            'video_changing': False,
            'error': result['reason']
        }
        print(json.dumps(output_result, ensure_ascii=False))
        sys.exit(1)
    
    sys.exit(0)