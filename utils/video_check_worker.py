#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step6 单个 URL 的画面变化检测，由 iptv_checker.py 在独立进程里调用：

    python utils/video_check_worker.py <url>

用 ffmpeg 解码视频，按流自身的时间戳每隔 SAMPLE_INTERVAL 秒取一帧（缩小成灰度图），
每取到一帧就和之前的帧比较：灰度变化超过 PIXEL_DIFF 的像素占比达到 MIN_CHANGED_RATIO 即判为画面有变化，
立刻结束（正常节目通常 2 帧就够了）。一直没有变化就继续取，最多 MAX_FRAMES 帧（约 18 秒）；
取满 STATIC_MIN_FRAMES 帧（约 8 秒）都没有变化才判为静止画面，网速太慢没取够时不下结论。

只数变化明显的像素，是为了不把压缩噪声当成画面变化：静止的占位画面（例如“流媒体测试源”）
相邻两帧之间会有上万个像素差 1~2 个灰度级，但几乎没有超过 15 的。

不用 OpenCV 读流：GitHub Actions 上 OpenCV 读 1080p、50/60 帧、MPEG-2 的流时会反复返回同一帧，
约 12% 正常播放的流被误判为静止。

结果以一行 JSON 输出到 stdout：
    {"success": true, "has_video": true, "video_changing": true/false/null, "frame_info": {...}}
    {"success": false, "error": "..."}   （同时以非 0 状态退出）
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np

USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

SAMPLE_INTERVAL = 2        # 取帧间隔（秒，按流的时间戳）
MAX_FRAMES = 10            # 一直没有变化时最多取几帧（约 18 秒）
STATIC_MIN_FRAMES = 5      # 至少取到几帧（约 8 秒）都没有变化，才判为静止画面
WIDTH, HEIGHT = 320, 180   # 缩小后比较，顺便平均掉一部分噪声
PIXEL_DIFF = 15            # 灰度变化超过它的像素才算“变了”
MIN_CHANGED_RATIO = 0.001  # 变了的像素占比达到 0.1% 才算画面有变化（静止画面为 0，正常节目 >= 0.8%）

# 单次取帧的时长上限（秒）；超时后用已经取到的帧判断
SAMPLE_TIMEOUT = int(os.environ.get('VIDEO_CHECK_TIMEOUT', 30))
MAX_ATTEMPTS = 2


# ffmpeg 7.1 起 HLS 分片地址必须带常见扩展名（.ts 等），amagi 等不带扩展名的跳转地址会被拒绝。
# 这两个是 HLS 专用选项，用在 flv、mp4 等输入上会报 “Option not found”，所以只在被拒绝后加上重试。
HLS_ANY_SEGMENT = ['-allowed_segment_extensions', 'ALL', '-extension_picky', '0']
HLS_SEGMENT_REJECTED = 'allowed_segment_extensions'


def _ffmpeg_cmd(url, any_segment=False):
    return [
        'ffmpeg', '-hide_banner', '-nostats', '-loglevel', 'error',
        '-user_agent', USER_AGENT,
        '-rw_timeout', '10000000',  # 10 秒收不到数据就放弃（微秒）
        *(HLS_ANY_SEGMENT if any_segment else []),
        '-i', url,
        '-map', '0:v:0',
        # 选第一帧，之后每隔 SAMPLE_INTERVAL 秒选一帧；passthrough 防止按恒定帧率补出重复帧
        '-vf', (f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{SAMPLE_INTERVAL})',"
                f"scale={WIDTH}:{HEIGHT}:flags=area,format=gray"),
        '-fps_mode', 'passthrough',
        '-frames:v', str(MAX_FRAMES),
        '-f', 'rawvideo', 'pipe:1',
    ]


def _changed_ratio(a, b) -> float:
    """灰度变化超过 PIXEL_DIFF 的像素占比"""
    return float(np.mean(np.abs(a - b) > PIXEL_DIFF))


def sample(url, any_segment=False):
    """边取帧边比较。返回 (取到的帧数, 最大变化占比, ffmpeg 的错误输出, 是否超时)"""
    frame_size = WIDTH * HEIGHT
    frames, max_ratio = [], 0.0
    with tempfile.TemporaryFile() as stderr:  # 不用管道，免得错误输出太多把 ffmpeg 堵住
        try:
            proc = subprocess.Popen(_ffmpeg_cmd(url, any_segment), stdout=subprocess.PIPE, stderr=stderr)
        except FileNotFoundError:
            return 0, 0.0, 'ffmpeg not found', False

        timer = threading.Timer(SAMPLE_TIMEOUT, proc.kill)  # 超时后杀掉 ffmpeg，下面的 read 随即返回
        timer.start()
        try:
            while len(frames) < MAX_FRAMES:
                data = proc.stdout.read(frame_size)
                if len(data) < frame_size:
                    break
                frame = np.frombuffer(data, np.uint8).reshape(HEIGHT, WIDTH).astype(np.int16)
                max_ratio = max([max_ratio] + [_changed_ratio(frame, f) for f in frames])
                frames.append(frame)
                if max_ratio >= MIN_CHANGED_RATIO:
                    break
        finally:
            timed_out = not timer.is_alive()
            timer.cancel()
            proc.kill()
            proc.wait()
            proc.stdout.close()

        stderr.seek(0)
        errors = stderr.read().decode('utf-8', 'ignore')
    return len(frames), max_ratio, errors, timed_out


def check(url):
    any_segment = False
    attempts = 0
    while True:
        count, ratio, errors, timed_out = sample(url, any_segment)
        if count >= 2 or timed_out:
            break
        if not any_segment and HLS_SEGMENT_REJECTED in errors:
            any_segment = True  # 不算一次重试
            continue
        attempts += 1
        if attempts >= MAX_ATTEMPTS:
            break
        time.sleep(2)

    if count < 2:
        lines = [line.strip() for line in errors.splitlines() if line.strip()]
        error = lines[-1][:200] if lines else ''
        if timed_out:
            error = f'timeout after {SAMPLE_TIMEOUT}s' + (f' ({error})' if error else '')
        reason = f'only {count} frame(s) decoded'
        return {'success': False, 'error': f'{reason}: {error}' if error else reason}

    if ratio >= MIN_CHANGED_RATIO:
        changing = True
    elif count >= STATIC_MIN_FRAMES:
        changing = False
    else:
        changing = None  # 取到的帧太少，判断不了是不是静止
    return {
        'success': True,
        'has_video': True,
        'video_changing': changing,
        'frame_info': {'frames': count, 'changed_ratio': round(ratio * 100, 3)},  # 百分比
    }


def main():
    if len(sys.argv) != 2:
        print(json.dumps({'success': False, 'error': 'usage: video_check_worker.py <url>'}))
        sys.exit(1)
    result = check(sys.argv[1])
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
