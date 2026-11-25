#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV检测工具 - Step6：画面变化与声音检测
输入 output/step5_speed_resources.csv（first.py 生成），
输出 output/step6_part1.csv、output/step6_part2.csv ...（供 third.py 合并使用）

为了让每次运行都在 GitHub Actions 的 6 小时上限内完成，Step6 按 URL 拆成 STEP6_PARTS 部分，
每部分由一个工作流在不同时间单独运行：

    python second.py --part 1     # 只检测第 1 部分，写 output/step6_part1.csv
    python second.py --part 2     # 只检测第 2 部分，写 output/step6_part2.csv
    python second.py              # 本地一次检测全部，按同样规则写出所有部分文件

Author: chaichunyang@outlook.com
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from iptv_checker import check_videos, print_step_stats
from utils.name_rules import NameRules
from utils.step_io import (
    STEP6_PARTS,
    ResultDropError,
    check_pass_rate,
    format_duration,
    read_pass_rate,
    read_step_resources,
    step6_part_file,
    step6_part_of,
    write_step_resources,
)

STEP5_FILE = Path("output/step5_speed_resources.csv")

# 通过率下限，低于它视为检测环境异常（正常约 80%，OpenCV 打不开 https 时约 20%）
STEP6_MIN_PASS_RATE = 0.35


def _setup_encoding():
    # 子进程（video_check_worker.py）继承这些环境变量，避免中文日志编码出错
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['LANG'] = 'C.UTF-8'
    os.environ['LC_ALL'] = 'C.UTF-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def _save_part(part: int, resources: List[Dict], tested: int) -> bool:
    """写出一个部分的结果；通过率骤降时不覆盖上一次的结果，返回 False"""
    output_file = step6_part_file(part)
    try:
        check_pass_rate(f"Step6 第{part}部分", len(resources), tested,
                        STEP6_MIN_PASS_RATE, read_pass_rate(output_file))
    except ResultDropError as e:
        print(f"❌ {e}")
        print(f"❌ 保留原有的 {output_file} 不覆盖")
        return False
    write_step_resources(output_file, resources,
                         f"Step6 第{part}/{STEP6_PARTS}部分: 画面变化与声音筛查后资源", tested)
    return True


def run_step6(part: Optional[int] = None) -> bool:
    """返回是否全部成功"""
    start_time = time.time()
    scope = f"第{part}/{STEP6_PARTS}部分" if part else f"全部（{STEP6_PARTS}个部分）"
    print("=" * 80)
    print(f"【IPTV检测工具 - Step6 {scope}】开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"输入文件：{STEP5_FILE}")
    print("=" * 80)

    if not STEP5_FILE.exists():
        print(f"❌ Step5结果文件不存在：{STEP5_FILE}")
        print("请先运行 first.py 完成 Step1~Step5")
        return False

    all_resources = read_step_resources(STEP5_FILE)
    if not all_resources:
        print("❌ Step5 CSV文件读取失败或为空")
        return False

    # Step3 已经筛过名称、去过重；这里再筛一次，模板删了关键词时不必等下一次 first.py
    rules = NameRules.load()
    speed_resources = []
    seen: Set[str] = set()
    for resource in all_resources:
        url = resource['url']
        if url in seen or not rules.matches(resource['name'], url):
            continue
        if part is None or step6_part_of(url) == part:
            seen.add(url)
            speed_resources.append(resource)
    print(f"📋 Step5 共 {len(all_resources)} 个资源，"
          f"本次检测 {scope}: {len(speed_resources)} 个（已去掉模板不收录的频道和重复 URL）")
    print_step_stats("Step5(从文件)", len(speed_resources), speed_resources, "从CSV文件加载")

    print("\n📊 Step6: 画面变化与有声音项目筛查")
    print("-" * 50)
    video_resources = check_videos(speed_resources)

    success_rate = len(video_resources) / len(speed_resources) * 100 if speed_resources else 0
    print()
    print_step_stats("Step6", len(speed_resources), video_resources, f"画面检测成功率: {success_rate:.1f}%")

    ok = True
    for current in ([part] if part else range(1, STEP6_PARTS + 1)):
        passed = [r for r in video_resources if step6_part_of(r['url']) == current]
        tested = sum(step6_part_of(r['url']) == current for r in speed_resources)
        ok = _save_part(current, passed, tested) and ok

    print(f"\n{'🎉' if ok else '❌'} Step6 {scope}{'完成' if ok else '结果异常'}！"
          f"耗时 {format_duration(time.time() - start_time)}")
    print("👉 third.py 会合并所有部分文件，继续 Step7 及以后的步骤")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Step6：画面变化与声音检测")
    parser.add_argument('--part', type=int, choices=range(1, STEP6_PARTS + 1),
                        help=f"只检测第几部分（1~{STEP6_PARTS}），不填则检测全部")
    args = parser.parse_args()

    _setup_encoding()
    if not run_step6(args.part):
        sys.exit(1)


if __name__ == "__main__":
    main()
