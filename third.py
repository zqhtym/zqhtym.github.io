#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
third.py - Step7 ~ Step8

Step7: 合并 Step6 各部分结果（output/step6_part*.csv），
       按 name_filtering_rules.txt 的分类顺序和关键词顺序，把 Step6 结果和 white.txt 白名单
       整理成 output/LE.txt（速度 >= 1.0 MB/s）和 output/LU.txt（速度 >= 0.2 MB/s），
       同一个 URL 只收录一次，同名频道按速度从快到慢排列
Step8: 把成人分类（分类名以 🔞 开头）从 LE / LU 里过滤掉，单独写到 output/LX.txt，
       再调用 utils/txt_to_m3u8b.py 把 LE / LU / LX 转成 m3u。
       LX 不提交到本仓库，由 third-only.yml 推送到私有仓库
"""

import re
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from utils.name_rules import NameRules, is_adult_category, keyword_matches, load_template
from utils.step_io import (
    STEP6_PARTS,
    check_count_drop,
    format_duration,
    read_step_resources,
    step6_part_file,
)

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8')

OUTPUT_DIR = Path("output")
WHITELIST_FILE = Path("white.txt")
CONVERTER = Path("utils/txt_to_m3u8b.py")

WHITELIST_SPEED = 5.0  # 白名单资源一律视为 5 MB/s，LE / LU 都会收录
ADULT_PREFIX = "LX"    # 成人内容的播放列表，收录范围与速度下限最低的列表（LU）相同
PLAYLISTS = [          # (文件名前缀, 最低速度 MB/s)
    ("LE", 1.0),
    ("LU", 0.2),
]

_CCTV_RE = re.compile(r'^(CCTV[-\s]*)(\d+)', re.IGNORECASE)


# ---------------------------------------------------------------- 输入

def load_step6() -> List[Dict]:
    """按顺序读取并合并 Step6 各部分文件；缺失的部分跳过并提示"""
    resources = []
    for part in range(1, STEP6_PARTS + 1):
        part_file = step6_part_file(part)
        if not part_file.exists():
            print(f"⚠️ 缺少 Step6 第{part}部分: {part_file}，本次不包含这部分频道")
            continue
        part_resources = read_step_resources(part_file)
        modified = datetime.fromtimestamp(part_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"📋 Step6 第{part}部分: {len(part_resources)} 个资源（{part_file}，修改时间 {modified}）")
        resources.extend(part_resources)
    return resources


def load_whitelist() -> List[Dict]:
    """读取 white.txt（格式：名称,URL）"""
    resources = []
    if not WHITELIST_FILE.exists():
        print(f"⚠️ 白名单文件不存在: {WHITELIST_FILE}")
        return resources

    with open(WHITELIST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or ',' not in line:
                continue
            name, url = (part.strip() for part in line.split(',', 1))
            if name and url.startswith('http'):
                resources.append({'name': name, 'url': url, 'speed': WHITELIST_SPEED, 'category': ''})

    print(f"📋 白名单资源: {len(resources)} 个")
    return drop_dead_whitelist(resources)


def _is_dead(url: str) -> bool:
    """地址确定已失效：两次都是 404/410，或域名无法解析。

    超时、403、5xx 等可能只是 GitHub Actions 的网络被限制，白名单里不算失效。
    """
    for attempt in range(2):
        if attempt:
            time.sleep(3)
        try:
            with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=10):
                return False
        except HTTPError as e:
            if e.code not in (404, 410):
                return False
        except URLError as e:
            if not isinstance(e.reason, socket.gaierror):
                return False
        except Exception:
            return False
    return True


def drop_dead_whitelist(resources: List[Dict]) -> List[Dict]:
    """去掉确定已失效的白名单频道"""
    with ThreadPoolExecutor(max_workers=10) as executor:
        dead_flags = list(executor.map(lambda r: _is_dead(r['url']), resources))

    dead = [r for r, flag in zip(resources, dead_flags) if flag]
    if len(dead) * 2 > len(resources):
        print(f"⚠️ 白名单有 {len(dead)} 个无法访问，超过一半，多半是本机网络问题，本次全部保留")
        return resources
    for resource in dead:
        print(f"⚠️ 白名单频道已失效，不收录: {resource['name']},{resource['url']}")
    return [r for r, flag in zip(resources, dead_flags) if not flag]


# ---------------------------------------------------------------- 排序

def _cctv_number(name: str) -> float:
    match = _CCTV_RE.search(name)
    return int(match.group(2)) if match else float('inf')


def sort_by_keyword_order(resources: List[Dict], keywords: List[str]) -> List[Dict]:
    """排序：模板里关键词的先后 → CCTV 编号 → 名称 → 速度（降序），同名频道最快的排在最前"""
    # 关键词重复出现（忽略大小写）时以最后一次出现的位置为准，与原逻辑保持一致
    positions = {keyword.lower(): index for index, keyword in enumerate(keywords)}

    def keyword_index(name: str) -> float:
        for keyword in keywords:
            if keyword_matches(keyword, name):
                return positions[keyword.lower()]
        return float('inf')

    return sorted(resources, key=lambda r: (
        keyword_index(r['name']),
        _cctv_number(r['name']),
        r['name'],
        -r.get('speed', 0),
    ))


# ---------------------------------------------------------------- 输出

def build_playlist(resources: List[Dict], template: List[Dict]) -> Tuple[List[str], int]:
    """按模板结构生成播放列表。每个 URL 只收录一次，归入第一个匹配的分类。返回 (所有行, 频道条数)"""
    rules = NameRules(template)
    by_category: Dict[int, List[Dict]] = {}
    for resource in resources:
        position = rules.rank(resource['name'], resource['url'])
        if position is not None:
            by_category.setdefault(position[0], []).append(resource)

    used = set()
    lines: List[str] = []
    count = 0
    category = -1
    for item in template:
        if item['type'] == 'empty':
            lines.append('')
        elif item['type'] == 'header':
            lines.append(item['content'])
        else:
            category += 1
            matched = []
            for resource in by_category.get(category, []):
                if resource['url'] not in used:
                    matched.append(resource)
                    used.add(resource['url'])
            for resource in sort_by_keyword_order(matched, item['keywords']):
                lines.append(f"{resource['name']},{resource['url']}")
                count += 1
    return lines, count


def count_channels(playlist: Path) -> int:
    """播放列表里现有的频道条数；文件不存在时为 0"""
    if not playlist.exists():
        return 0
    with open(playlist, 'r', encoding='utf-8') as f:
        return sum('://' in line for line in f)


def build_playlists(video_resources: List[Dict]) -> Dict[str, List[str]]:
    """Step7：按模板分类，返回 {文件名前缀: 所有行}（还包含成人分类，Step8 再分出去）"""
    template = load_template()
    categories = [item['name'] for item in template if item['type'] == 'category']
    print(f"📋 分类模板: {len(categories)} 个分类")

    # 白名单在前：同一个 URL 两边都有时，用白名单里的名称
    candidates = load_whitelist() + video_resources

    playlists = {}
    for prefix, min_speed in PLAYLISTS:
        selected = [r for r in candidates if r.get('speed', 0) >= min_speed]
        playlists[prefix], count = build_playlist(selected, template)
        print(f"📄 {prefix}: {count} 条 (速度 >= {min_speed} MB/s，"
              f"候选 {len(selected)} 条，未匹配任何分类的不收录)")

    print(f"📊 Step6 频道数: {len(set(r['name'] for r in video_resources))}")
    return playlists


def split_adult(lines: List[str]) -> Tuple[List[str], List[str]]:
    """把成人分类从播放列表里分出来，返回 (普通行, 成人行)"""
    normal: List[str] = []
    adult: List[str] = []
    target = normal
    for line in lines:
        if '#genre#' in line:
            target = adult if is_adult_category(line) else normal
        target.append(line)
    while normal and not normal[-1]:
        normal.pop()
    return normal, adult


def write_playlists(playlists: Dict[str, List[str]]) -> List[str]:
    """Step8：过滤成人内容后写出 LE / LU，成人内容写到 LX。返回写出的文件名前缀"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    outputs = {}
    adult: List[str] = []
    for prefix, _ in PLAYLISTS:
        normal, adult = split_adult(playlists[prefix])  # 最后一个列表（LU）的速度下限最低，收录最全
        # 先检查完所有列表再写文件，避免 LE、LU 一个新一个旧
        output_file = OUTPUT_DIR / f"{prefix}.txt"
        count = sum('://' in line for line in normal)
        check_count_drop(f"Step8 {output_file.name}", count, count_channels(output_file))
        outputs[prefix] = normal
        print(f"📄 {prefix}: 过滤成人内容 {sum('://' in line for line in adult)} 条，写入 {count} 条")

    # 没有成人内容时不写 LX，避免用空列表覆盖
    if any('://' in line for line in adult):
        outputs[ADULT_PREFIX] = adult
        print(f"📄 {ADULT_PREFIX}: 写入 {sum('://' in line for line in adult)} 条")

    for prefix, lines in outputs.items():
        with open(OUTPUT_DIR / f"{prefix}.txt", 'w', encoding='utf-8') as f:
            f.writelines(line + '\n' for line in lines)
    return list(outputs)


def convert_to_m3u(prefixes: List[str]):
    """Step8：txt -> m3u"""
    for prefix in prefixes:
        txt_file = OUTPUT_DIR / f"{prefix}.txt"
        m3u_file = OUTPUT_DIR / f"{prefix}.m3u"
        print(f"🔄 转换 {txt_file.name} -> {m3u_file.name}")
        subprocess.run([sys.executable, str(CONVERTER), str(txt_file), str(m3u_file)],
                       check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"✅ 转换完成: {m3u_file}")


def verify_outputs(prefixes: List[str]):
    print("\n🔍 检查生成的文件")
    print("-" * 50)
    for prefix in prefixes:
        for suffix in ('.txt', '.m3u'):
            path = OUTPUT_DIR / f"{prefix}{suffix}"
            if not path.exists():
                print(f"❌ {path.name}: 不存在")
                continue
            stat = path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"✅ {path.name}: {stat.st_size} 字节，修改时间 {modified}")
            if stat.st_size == 0:
                print(f"⚠️ {path.name} 是空文件")


def run():
    print("=" * 80)
    print("IPTV检测工具 - Step7 ~ Step8：按模板分类生成 LE / LU 播放列表")
    print("=" * 80)
    start_time = time.time()

    video_resources = load_step6()
    if not video_resources:
        sys.exit("❌ 没有可用的 Step6 结果（output/step6_part*.csv 都不存在或为空）")
    print(f"📋 合并后 Step6 资源: {len(video_resources)} 个")

    print("\n📊 Step7: 按模板分类")
    print("-" * 50)
    playlists = build_playlists(video_resources)

    print("\n📊 Step8: 过滤成人内容，写出播放列表并转换为 m3u")
    print("-" * 50)
    prefixes = write_playlists(playlists)
    convert_to_m3u(prefixes)

    print(f"\n🎉 完成！耗时 {format_duration(time.time() - start_time)}")
    verify_outputs(prefixes)


if __name__ == "__main__":
    run()
