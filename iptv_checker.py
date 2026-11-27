#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV 检测核心模块：Step6 画面变化检测，供 second.py 使用。

每个 URL 都在独立进程里调用 utils/video_check_worker.py 检测（ffmpeg 取帧比较），
避免 ffmpeg 卡住或崩溃时拖垮主进程。
Author: chaichunyang@outlook.com
"""

import json
import multiprocessing
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

WORKER_SCRIPT = Path(__file__).resolve().parent / "utils" / "video_check_worker.py"

# GitHub Actions 上分批检测，批次之间稍作停顿，避免被源站限流
GITHUB_BATCH_SIZE = 50
GITHUB_BATCH_PAUSE = 2


def _is_github_actions() -> bool:
    return bool(os.environ.get('GITHUB_ACTIONS'))


def _decode(data: bytes) -> str:
    for encoding in ('utf-8', 'gbk'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode('latin1', errors='ignore')


def _parse_worker_json(output: str):
    """从 worker 的输出里找出 JSON 结果行（worker 还会打印 [Debug] 日志）"""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return None


def _failure(reason: str) -> Dict:
    return {'has_video': False, 'video_changing': False, 'reason': reason, 'success': False}


def check_video_changes(url: str) -> Dict:
    """检测单个 URL 的画面有没有变化（调用 utils/video_check_worker.py）"""
    timeout = int(os.environ.get('VIDEO_TOTAL_TIMEOUT', 180))
    try:
        result = subprocess.run(
            [sys.executable, str(WORKER_SCRIPT), url],
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return _failure(f'画面检测超时（{timeout}秒）')
    except Exception as e:
        return _failure(f'检测异常: {e}')

    video_result = _parse_worker_json(_decode(result.stdout))

    if result.returncode != 0:
        # worker 失败时会把原因写在 JSON 的 error 字段里
        reason = (video_result or {}).get('error') or _decode(result.stderr).strip() or '未知错误'
        return _failure(f'取帧失败: {reason}')

    if video_result is None:
        return _failure(f'无法解析JSON输出: {_decode(result.stdout)}')

    return {
        'has_video': video_result.get('has_video', False),
        'video_changing': video_result.get('video_changing', False),
        'frame_info': video_result.get('frame_info', {}),
        'reason': video_result.get('error') or '',
        'success': video_result.get('success', False),
    }


def is_valid_stream(result: Dict) -> bool:
    """能读到画面，并且画面不是静止的。

    静止画面多半是“频道已停播”“流媒体测试源”之类的占位图，即使带着背景音乐也淘汰；
    网速太慢、取到的帧不够判断（video_changing 为 None）时不淘汰。
    """
    return bool(result['success'] and result['has_video']) and result['video_changing'] is not False


def _diagnose(reason: str) -> str:
    """GitHub Actions 上给失败原因加一句诊断，方便看日志"""
    lower = reason.lower()
    if '404' in reason:
        return "URL失效 (404错误)"
    if 'timeout' in lower or '超时' in reason:
        return "网络超时 (可能被限制)"
    if 'connect' in lower:
        return "连接失败 (网络限制)"
    if '403' in reason:
        return "访问被拒绝 (403，可能IP被限制)"
    if 'ffmpeg not found' in reason:
        return "没有安装 ffmpeg"
    return f"其他错误 - {reason}"


def _worker_count() -> int:
    if _is_github_actions():
        workers = int(os.environ.get('GITHUB_ACTIONS_WORKERS', 3))
        print(f"GitHub Actions环境，使用保守并发数: {workers} (避免网络限制)")
        return workers
    cpu_count = multiprocessing.cpu_count()
    workers = min(cpu_count * 2, 16, max(4, cpu_count))
    print(f"本地环境，CPU核心数: {cpu_count}，使用并发数: {workers}")
    return workers


def check_videos(resources: List[Dict]) -> List[Dict]:
    """并发检测所有资源，返回通过 is_valid_stream 的资源（附带检测结果字段）"""
    total = len(resources)
    print(f"开始画面变化检测，共{total}个URL...")
    if not total:
        return []

    on_github = _is_github_actions()
    max_workers = _worker_count()
    batch_size = GITHUB_BATCH_SIZE if on_github else total
    batches = [resources[i:i + batch_size] for i in range(0, total, batch_size)]

    valid = []
    processed = 0
    for index, batch in enumerate(batches, 1):
        if len(batches) > 1:
            print(f"🔄 处理第{index}/{len(batches)}批 (资源: {len(batch)}个)", flush=True)

        batch_valid = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_video_changes, r['url']): r for r in batch}
            for future in as_completed(futures):
                resource = futures[future]
                processed += 1
                name = resource.get('name', '未知频道')[:30]
                try:
                    result = future.result()
                except Exception as e:
                    print(f"❌ 处理检测结果异常: {e}")
                    continue

                info = result.get('frame_info', {})
                ratio = info.get('changed_ratio')
                if is_valid_stream(result):
                    valid.append({**resource, **result})
                    batch_valid += 1
                    detail = (f"画面变化 {ratio}%" if result['video_changing']
                              else f"只取到 {info.get('frames')} 帧，未确定是否静止")
                    print(f"✅ [{processed}/{total}] {name} - {detail}", flush=True)
                elif result['success']:
                    # 附上 URL，方便人工核对是不是真的静止
                    print(f"❌ [{processed}/{total}] {name} - 静止画面（变化像素 {ratio}%） "
                          f"{resource['url']}", flush=True)
                else:
                    reason = result.get('reason', '')
                    print(f"❌ [{processed}/{total}] {name} - {reason[:60]}", flush=True)
                    if on_github:
                        print(f"🔍 GitHub Actions诊断: {_diagnose(reason)}")

        if len(batches) > 1:
            print(f"✅ 第{index}批完成，有效资源: {batch_valid}个", flush=True)
            if index < len(batches):
                print(f"⏱️ 批次间暂停{GITHUB_BATCH_PAUSE}秒，避免网络限制...", flush=True)
                time.sleep(GITHUB_BATCH_PAUSE)

    print(f"\n✅ 画面检测完成，有效资源: {len(valid)} 个")
    return valid


def print_step_stats(step_name: str, input_count: int, output_resources: List[Dict], description: str) -> None:
    """打印步骤统计（含分类统计）"""
    print(f"📊 {step_name}完成:")
    print(f"   输入资源: {input_count}")
    print(f"   输出资源: {len(output_resources)}")
    print(f"   {description}")

    if output_resources:
        counts: Dict[str, int] = {}
        for resource in output_resources:
            category = resource.get('category', '默认分类')
            counts[category] = counts.get(category, 0) + 1
        print("📋 分类统计:")
        for category, count in sorted(counts.items()):
            print(f"   {category}: {count} 个")
