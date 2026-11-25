# -*- coding: utf-8 -*-
"""
频道匹配规则（name_filtering_rules.txt）。

分类下面每行一个频道名关键词；写成 url:xxx 的行按 URL 匹配，并且优先于所有频道名关键词
（用来把某个站点的内容全部归到一个分类，不会因为名称碰巧匹配而跑到别的分类）。

分类名以 🔞 开头的是成人分类：它的关键词优先于其他分类，Step8 会把它从 LE / LU 里分到 LX。

first.py（Step3 筛选）、second.py（Step6 筛选）和 third.py（Step7 分类）共用这里的判断，
保证前面筛掉的一定是 Step7 不会收录的频道：既不浪费检测时间，也不会多删。
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

RULES_FILE = Path("name_filtering_rules.txt")

URL_PREFIX = 'url:'
ADULT_MARK = '🔞'

# 成人内容里名称指向未成年人或非自愿的，任何列表都不收录
_FORBIDDEN_RE = re.compile(
    r'幼|童|萝莉|蘿莉|ロリ|loli|未成年|小学|小學|初中|高中|中学|中學|国中|國中|女高|学生|學生|同桌|同学|同學|少女'
    r'|teen|school|underage|(?<![a-z])jk(?![a-z])|(?<!\d)(?:\d|1[0-7])\s*[岁歲]'
    r'|偷拍|盗撮|迷奸|迷姦|强奸|強姦|轮奸|輪姦|强暴|強暴|凌辱|(?<![a-z])rape',
    re.IGNORECASE,
)

_IGNORED_RE = re.compile(r'[\s!]+')


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


def is_adult_category(title: str) -> bool:
    return title.strip().startswith(ADULT_MARK)


def load_template(path: Path = RULES_FILE) -> List[Dict]:
    with open(path, 'r', encoding='utf-8-sig') as f:
        return parse_template(f.readlines())


@lru_cache(maxsize=None)
def _keyword_pattern(keyword: str) -> Optional[Pattern]:
    chars = _IGNORED_RE.sub('', keyword.lower())
    if not chars:
        return None
    # 英文关键词前面不能紧挨着字母，数字开头的关键词前面不能紧挨着数字，
    # 否则 HOT 会命中 Schlosshotel、4k 会命中 24KZ。后面不限制（BBC 要能命中 BBCNews）。
    if 'a' <= chars[0] <= 'z':
        prefix = r'(?<![a-z])'
    elif chars[0].isdigit():
        prefix = r'(?<!\d)'
    else:
        prefix = ''
    return re.compile(prefix + r'[\s!]*'.join(map(re.escape, chars)))


def keyword_matches(keyword: str, name: str) -> bool:
    """频道名是否包含关键词（忽略大小写、空格和 !）"""
    pattern = _keyword_pattern(keyword)
    return bool(pattern and pattern.search(name.lower()))


class NameRules:
    """判断频道名会不会被模板收录"""

    def __init__(self, template: List[Dict]):
        self._names: List[Tuple[Tuple[int, int], str]] = []
        self._urls: List[Tuple[Tuple[int, int], str]] = []
        adult_names: List[Tuple[Tuple[int, int], str]] = []
        self._adult_categories = set()
        categories = [item for item in template if item['type'] == 'category']
        for c, item in enumerate(categories):
            adult = is_adult_category(item['name'])
            if adult:
                self._adult_categories.add(c)
            for k, keyword in enumerate(item['keywords']):
                if keyword.lower().startswith(URL_PREFIX):
                    url_keyword = keyword[len(URL_PREFIX):].strip().lower()
                    if url_keyword:
                        self._urls.append(((c, k), url_keyword))
                else:
                    (adult_names if adult else self._names).append(((c, k), keyword))
        if not self._names:
            raise ValueError(f"分类模板里没有任何频道名关键词: {RULES_FILE}")
        self._names = adult_names + self._names
        self._cache: Dict[str, Optional[Tuple[int, int]]] = {}

    @classmethod
    def load(cls, path: Path = RULES_FILE) -> 'NameRules':
        return cls(load_template(path))

    def _position(self, name: str, url: str) -> Optional[Tuple[int, int]]:
        url_lower = url.lower()
        for position, keyword in self._urls:
            if keyword in url_lower:
                return position
        if name not in self._cache:
            self._cache[name] = next(
                (position for position, keyword in self._names if keyword_matches(keyword, name)), None)
        return self._cache[name]

    def is_forbidden(self, name: str, url: str) -> bool:
        """属于成人分类，且名称指向未成年人或非自愿内容"""
        position = self._position(name, url)
        return position is not None and position[0] in self._adult_categories \
            and bool(_FORBIDDEN_RE.search(name))

    def rank(self, name: str, url: str) -> Optional[Tuple[int, int]]:
        """命中的 (分类序号, 关键词序号)；没有命中或不允许收录时返回 None"""
        return None if self.is_forbidden(name, url) else self._position(name, url)

    def matches(self, name: str, url: str) -> bool:
        return self.rank(name, url) is not None
