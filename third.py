#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
third.py - Step7 ~ Step8

Step7: 合并 Step6 各部分结果（output/step6_part*.csv），
       按 name_filtering_rules.txt 的分类顺序和关键词顺序，把 Step6 结果和 white.txt 白名单
       整理成 output/LE.txt（速度 >= 1.0 MB/s）和 output/LU.txt（速度 >= 0.2 MB/s）
Step8: 调用 utils/txt_to_m3u8b.py 把 LE.txt / LU.txt 转成 LE.m3u / LU.m3u
"""

import re
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from utils.step_io import STEP6_PARTS, format_duration, read_step_resources, step6_part_file

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8')

OUTPUT_DIR = Path("output")
RULES_FILE = Path("name_filtering_rules.txt")
WHITELIST_FILE = Path("white.txt")
CONVERTER = Path("utils/txt_to_m3u8b.py")

WHITELIST_SPEED = 5.0  # 白名单资源一律视为 5 MB/s，LE / LU 都会收录
PLAYLISTS = [          # (文件名前缀, 最低速度 MB/s)
    ("LE", 1.0),
    ("LU", 0.2),
]

_CCTV_RE = re.compile(r'^(CCTV[-\s]*)(\d+)', re.IGNORECASE)
_URL_SPEED_RE = re.compile(r'\.speed=(\d+(?:\.\d+)?)')


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
    return resources


def parse_template(lines: List[str]) -> List[Dict]:
    """解析分类模板，保留空行和分类标题行，输出时按原样写回。

    返回的条目有三种：
      {'type': 'empty'}                                  空行
      {'type': 'header', 'content': '☘️欧美,#genre#'}    分类标题行
      {'type': 'category', 'name': ..., 'keywords': [...]}  该分类的频道写在这里
    """
    structure = []
    current_category = None
    current_keywords: List[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            structure.append({'type': 'empty', 'content': ''})
            continue

        if '#genre#' in line:
            if current_category:
                structure.append({'type': 'category', 'name': current_category, 'keywords': current_keywords})
            current_category = line.split('#genre#')[0].strip()
            current_keywords = []
            structure.append({'type': 'header', 'content': line})
        elif current_category:
            current_keywords.append(line)

    if current_category:
        structure.append({'type': 'category', 'name': current_category, 'keywords': current_keywords})

    return structure


# ---------------------------------------------------------------- 匹配与排序

def _normalize(text: str) -> str:
    return text.replace(' ', '').replace('!', '').lower()


def keyword_matches(keyword: str, name: str) -> bool:
    """频道名是否包含关键词（忽略大小写；去掉空格和 ! 后再比一次）"""
    return _normalize(keyword) in _normalize(name) or keyword.lower() in name.lower()


def _cctv_number(name: str) -> float:
    match = _CCTV_RE.search(name)
    return int(match.group(2)) if match else float('inf')


def _url_speed(url: str) -> float:
    match = _URL_SPEED_RE.search(url)
    return float(match.group(1)) if match else 0


def sort_by_keyword_order(resources: List[Dict], keywords: List[str]) -> List[Dict]:
    """排序：模板里关键词的先后 → CCTV 编号 → URL 中 .speed= 的值（降序）→ 名称"""
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
        -_url_speed(r['url']),
        r['name'],
    ))


# ---------------------------------------------------------------- 输出

def write_playlist(output_file: Path, resources: List[Dict], template: List[Dict]) -> int:
    """按模板结构写出播放列表。每个资源只归入第一个匹配的分类，返回写入条数"""
    used = set()
    count = 0
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in template:
            if item['type'] == 'empty':
                f.write('\n')
            elif item['type'] == 'header':
                f.write(item['content'] + '\n')
            else:
                matched = []
                for resource in resources:
                    resource_id = (resource['name'], resource['url'])
                    if resource_id in used:
                        continue
                    if any(keyword_matches(k, resource['name']) for k in item['keywords']):
                        matched.append(resource)
                        used.add(resource_id)
                for resource in sort_by_keyword_order(matched, item['keywords']):
                    f.write(f"{resource['name']},{resource['url']}\n")
                    count += 1
    return count


def generate_playlists(video_resources: List[Dict]) -> bool:
    """Step7：生成 LE.txt / LU.txt"""
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not RULES_FILE.exists():
        print(f"❌ 分类模板不存在: {RULES_FILE}")
        return False
    with open(RULES_FILE, 'r', encoding='utf-8') as f:
        template = parse_template(f.readlines())
    categories = [item['name'] for item in template if item['type'] == 'category']
    print(f"📋 分类模板: {len(categories)} 个分类")

    whitelist = load_whitelist()
    candidates = video_resources + whitelist  # Step6 资源在前，白名单在后

    for prefix, min_speed in PLAYLISTS:
        selected = [r for r in candidates if r.get('speed', 0) >= min_speed]
        output_file = OUTPUT_DIR / f"{prefix}.txt"
        count = write_playlist(output_file, selected, template)
        print(f"📄 {output_file}: 写入 {count} 条 (速度 >= {min_speed} MB/s，"
              f"候选 {len(selected)} 条，未匹配任何分类的不写入)")

    print(f"📊 Step6 频道数: {len(set(r['name'] for r in video_resources))}")
    return True


def convert_to_m3u():
    """Step8：LE.txt / LU.txt -> LE.m3u / LU.m3u"""
    if not CONVERTER.exists():
        print(f"❌ 找不到转换脚本: {CONVERTER}")
        return

    for prefix, _ in PLAYLISTS:
        txt_file = OUTPUT_DIR / f"{prefix}.txt"
        m3u_file = OUTPUT_DIR / f"{prefix}.m3u"
        if not txt_file.exists():
            continue
        print(f"🔄 转换 {txt_file.name} -> {m3u_file.name}")
        try:
            subprocess.run([sys.executable, str(CONVERTER), str(txt_file), str(m3u_file)],
                           check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            print(f"✅ 转换完成: {m3u_file}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"❌ 转换失败: {e}")


def verify_outputs():
    print("\n🔍 检查生成的文件")
    print("-" * 50)
    for prefix, _ in PLAYLISTS:
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
        print("❌ 没有可用的 Step6 结果（output/step6_part*.csv 都不存在或为空）")
        return
    print(f"📋 合并后 Step6 资源: {len(video_resources)} 个")

    print("\n📊 Step7: 按模板分类生成 LE.txt / LU.txt")
    print("-" * 50)
    if not generate_playlists(video_resources):
        return

    print("\n📊 Step8: 转换为 m3u")
    print("-" * 50)
    convert_to_m3u()

    print(f"\n🎉 完成！耗时 {format_duration(time.time() - start_time)}")
    verify_outputs()


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"❌ Step7 失败: {e}")
        traceback.print_exc()
