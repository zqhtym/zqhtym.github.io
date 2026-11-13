#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV检测工具 - Step6：画面变化与声音检测
输入 output/step5_speed_resources.csv（first.py 生成），
输出 output/step6_video_resources.csv（供 third.py 使用）
Author: chaichunyang@outlook.com
"""

import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from iptv_checker import check_videos, print_step_stats
from utils.step_io import format_duration, read_step_resources, write_step_resources

STEP5_FILE = Path("output/step5_speed_resources.csv")
STEP6_FILE = Path("output/step6_video_resources.csv")


def _setup_encoding():
    # 子进程（video_check_worker.py）继承这些环境变量，避免中文日志编码出错
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['LANG'] = 'C.UTF-8'
    os.environ['LC_ALL'] = 'C.UTF-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def run_step6():
    start_time = time.time()
    print("=" * 80)
    print(f"【IPTV检测工具 - Step6】开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"输入文件：{STEP5_FILE}")
    print("=" * 80)

    if not STEP5_FILE.exists():
        print(f"❌ Step5结果文件不存在：{STEP5_FILE}")
        print("请先运行 first.py 完成 Step1~Step5")
        return

    speed_resources = read_step_resources(STEP5_FILE)
    if not speed_resources:
        print("❌ Step5 CSV文件读取失败或为空")
        return

    print_step_stats("Step5(从文件)", len(speed_resources), speed_resources, "从CSV文件加载")

    print("\n📊 Step6: 画面变化与有声音项目筛查")
    print("-" * 50)
    video_resources = check_videos(speed_resources)

    success_rate = len(video_resources) / len(speed_resources) * 100
    print()
    print_step_stats("Step6", len(speed_resources), video_resources, f"画面检测成功率: {success_rate:.1f}%")

    if not video_resources:
        # 全部失败多半是网络被限制，不要用空结果覆盖上一次的 step6 文件
        print(f"⚠️ 没有任何资源通过画面检测，保留原有的 {STEP6_FILE} 不覆盖")
        return

    write_step_resources(STEP6_FILE, video_resources, "Step6: 画面变化与声音筛查后资源")

    print(f"\n🎉 Step6完成！耗时 {format_duration(time.time() - start_time)}")
    print(f"📄 已生成 {STEP6_FILE}，包含 {len(video_resources)} 个资源")
    print("👉 请运行 third.py 继续 Step7 及以后的步骤")


def main():
    _setup_encoding()
    try:
        run_step6()
    except Exception as e:
        print(f"❌ Step6 失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
