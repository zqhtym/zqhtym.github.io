# -*- coding: utf-8 -*-
"""
步骤文件（output/stepN_*.csv）的读写，以及几个脚本共用的小工具。

步骤文件有两种格式：
1. first.py 输出的标准 CSV（step1~step5）：
       resource_name,url[,speed_mb]
       CCTV1,http://example.com/1.m3u8,0.62900
2. second.py 输出的分组格式（step6）：
       # Step6: ...            <- 文件头注释
       # [默认分类] 0.582MB/s   <- 分组行：分类名 + 平均速度
       CCTV1,http://example.com/1.m3u8,0.62900
"""

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_CATEGORY = "默认分类"

_GROUP_RE = re.compile(r'^#\s*\[(.*?)\]\s*([\d.]+)\s*MB/s')


def format_duration(seconds: float) -> str:
    """把秒数格式化成 “X小时Y分Z秒”"""
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}小时{minutes}分{secs}秒"
    if minutes:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


def read_csv_rows(path) -> List[List[str]]:
    """读取带表头的标准 CSV，返回表头之后的所有行"""
    with open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        next(reader, None)  # 跳过表头
        return list(reader)


def write_csv_rows(path, header: Sequence[str], rows: Iterable[Sequence]) -> None:
    """写出带表头的标准 CSV（URL 里有逗号时会自动加引号）"""
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def _split_fields(fields: List[str]) -> Tuple[str, str, Optional[float]]:
    """把一行拆成 (名称, URL, 速度)。

    速度只可能在第 3 列及以后的最后一列；URL 没加引号又含逗号时，中间几列拼回 URL。
    """
    name = fields[0].strip()
    rest = fields[1:]
    speed = None
    if len(rest) >= 2:
        try:
            speed = float(rest[-1])
            rest = rest[:-1]
        except ValueError:
            pass
    url = ','.join(rest).strip()
    return name, url, speed


def read_step_resources(path) -> List[Dict]:
    """读取步骤文件（两种格式都支持），返回 [{'name', 'url', 'speed', 'category'}]。

    行内没有速度时，用所在分组行的平均速度。
    """
    resources = []
    category = DEFAULT_CATEGORY
    group_speed = 0.0

    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith('#'):
                match = _GROUP_RE.match(line)
                if match:
                    category = match.group(1).strip() or category
                    try:
                        group_speed = float(match.group(2))
                    except ValueError:
                        group_speed = 0.0
                continue

            fields = next(csv.reader([line]))
            if len(fields) < 2:
                continue
            name, url, speed = _split_fields(fields)
            if name and url.startswith('http'):
                resources.append({
                    'name': name,
                    'url': url,
                    'speed': group_speed if speed is None else speed,
                    'category': category,
                })

    return resources


def _average_speed(resources: Iterable[Dict]) -> float:
    speeds = [r.get('speed', 0) for r in resources if r.get('speed', 0) > 0]
    return sum(speeds) / len(speeds) if speeds else 0.0


def write_step_resources(path, resources: List[Dict], description: str) -> None:
    """按分组格式写出步骤文件，每行为 “名称,URL,速度”"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    groups: Dict[str, List[Dict]] = {}
    for resource in resources:
        groups.setdefault(resource.get('category') or DEFAULT_CATEGORY, []).append(resource)

    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(f"# {description}\n")
        f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 资源数量: {len(resources)}\n")
        if resources:
            f.write(f"# 平均速度: {_average_speed(resources):.3f} MB/s\n")
        f.write("#" * 50 + "\n\n")

        writer = csv.writer(f, lineterminator='\n')
        for category, items in groups.items():
            f.write(f"# [{category}] {_average_speed(items):.3f}MB/s\n")
            for resource in items:
                writer.writerow([resource['name'], resource['url'], f"{resource.get('speed', 0):.5f}"])
            f.write("\n")

    print(f"📄 已生成: {path}")
