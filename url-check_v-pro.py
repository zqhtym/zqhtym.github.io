#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: chaichunyang@outlook.com

# 优化配置：解决GitHub Actions内存和编码问题
import os
import sys
import gc

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'

# 配置stdout编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 内存优化配置
gc.set_threshold(700, 10, 10)

'''


依照m3u-tester.py，解决对http://129.211.14.102:50085/sub?7pVBnFZv=txt上各条内容的测试，结果输出到C:\exe\m3u-tester-master\DG\live+{standard}+{daytime}.txt，要求，1分组，第一类分组，按央视、卫视、港澳台、其它；在第一类分组之下，再按4D或超高清、高清或HD、SD分类分组；2按item.speed > 1024 * 1024,standard=excellent; 按item.speed > 1024 * 700, standard=wonderful; item.speed > 1024 * 500,standard=good; item.speed > 1024 * 200 , standard=usefull输出。

要求测试结果输出 到C:\exe\m3u-tester-master\DG\live+{standard}+{daytime}.txt文件，如果standard=excellent、wonderful、good、useful， .txt文件应该有四个

请作如下 修改：1target_url 增加  https://gh-proxy.com/https://raw.githubusercontent.com/yoursmile66/TVBox/main/live.txt 、 https://gh-proxy.com/https://github.moeyy.xyz/https://raw.githubusercontent.com/dxawi/0/main/tvlive.txt、https://d.h6room.com/frjzb.txt；2增加404预筛查


结果输出到C:\exe\m3u-tester-master\DG\live+{standard}+{daytime}.txt，要求，1分组，第一类分组，按央视、卫视、港澳台、欧美、其它；在第一类分组之下，再按4D或超高清、高清或HD、SD分类分组；2按item.speed > 1024 * 1024,standard=excellent; 按item.speed > 1024 * 700, standard=wonderful; item.speed > 1024 * 500,standard=good; item.speed > 1024 * 200 , standard=usefull输出。3 所有cctv均按序放置在央视分组，所有名称有卫视均按序放置在卫视分组，其它分组中，只保留标题上包含有新闻、电影、高清、4K、>1080p、.mp4、四川、成都、江苏、南京、上海的节目；4 检测过程增加显示进程，如检测到xx个/总数xxx个；4 输出文件为，.txt


在url-fsfz-txt.py的基础上增加了"在执行for standard, min_speed in speed_levels.items():   之后，增加对同名，如cctv1（区分大小写），按照.speed数值，从大到小排序。"

要求按模块化重新梳理，每个模块相对独立
step1 初始化
step2 模块，读入所有的资源，网上本地
step3 ，对所有url去重，保留有name特征的url
step4 ，对名称、url筛查
名称、url筛查与7.2 一致
step5 ，做404筛查，
step6 ，进行速度筛查。
step7 ，结果整理
7.1 按响应速度分为excellent、wonderful、good、useful四级
7.2 同级中，按"央视"、"卫视"、"港澳台"、"欧美"、"其它"作第一类分组
"央视":  cctv|央视|中国中央电视台'; "卫视":名称中包含"卫视"；
"港澳台"：名称中包含'凤凰|无线|明珠|环球|美亚|翡翠|台视|中视|华视|中天|亚洲'；
"欧美"：名称中包含'al|ABC|BBC|Bloom|CBS|City|FOX|GB|go2|NBC|News|NTD|UN|Yah|trt'；
"其它"：名称中包含'4K|电影|四川|成都|上海|江苏|南京|新闻|高清|1080p' 或url以'.mp4'结尾
7.3 在同一类分组中，再按按4D或超高清、高清或HD、SD分类顺序排列
7.4 在顺序排列的同名如cctv1（区分大小写），按照url的.speed数值，从大到小排序。

step8 , 输出
输出 到C:\exe\m3u-tester-master\DG\live+{standard}+{daytime}.txt文件
# 关闭远端  275
上一版 url-fsfz-txt0.py

2. 404 筛查多进程实现
• 使用multiprocessing.Pool创建 10 个进程池
• 通过Manager().dict()实现多进程进度共享
• _check_404_worker函数作为工作进程，独立检测每个 URL 的 404 状态
• 增加超时控制（10 分钟），超时自动终止并返回空列表
• 实时输出检测进度（每处理 10 个条目更新一次）
3. 速度筛查多进程实现
• 使用multiprocessing.Pool创建 8 个进程池
• _test_speed_worker函数作为工作进程，独立测速每个流地址
• 保持原有测速逻辑（解析真实流地址、5 秒测速、计算 bytes/s）
• 同样增加 10 分钟超时控制，避免无限阻塞
• 实时输出测速进度
4. 关键兼容处理
• 修复 Windows 系统多进程freeze_support()问题
• 使用functools.partial传递共享进度字典
• 超时控制通过signal信号实现，兼容跨平台
• 进程池异常处理（超时自动 terminate）
5. 进度可视化
• 404 检测和速度检测均实时输出进度（\r回车符覆盖当前行）
• 每处理 10 个条目更新一次进度，减少 IO 开销
• 最终输出各步骤的数量统计（原始数→通过数）
267 if filename.endswith('.m3u') or filename.endswith('.m3u8'):
180       #if self.url.lower().endswith('.mp4'):
        #    return '其它'
要求在speed_test_items = test_speed(no_404_items)之后，增加画面检测，即要求1有声音有图面；2图面15秒内内容在变化
增加  Step9    def save_speed_to_temp(speed_test_items, temp_file_path="temp_speed.txt") 
#              def load_speed_from_temp( )
# -*- coding: utf-8 -*-
# Author: chaichunyang@outlook.com

pip install opencv-python  import cv2
'''
import json
import os
import sys
import time
import re
import cv2
import pytz
import shutil
import subprocess
import threading
import numpy as np
from pathlib import Path
import multiprocessing
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime
from multiprocessing import Manager
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
from functools import partial
from urllib.parse import unquote, urlparse, quote, urlunparse
from pymediainfo import MediaInfo



# ======================== 全局配置模块 ========================
class Config:
    """全局配置类"""
    # 远程资源地址
    REMOTE_URLS = [
        "http://lisha521.dynv6.net.fh4u.org/tv.txt",         
        "http://rihou.cc:555/gggg.nzk",        
        "https://cloud.7so.top/f/yr7BHL/HKTV.txt",
        "https://d.kstore.dev/download/15114/gztv.txt",    
        "https://d.kstore.dev/download/15114/HKTV.txt",
        "https://gitee.com/alexkw/app/raw/master/kgk.txt",        
        "https://gitee.com/jin-xueling/lingl/raw/master/hu.txt",
        "https://gitee.com/main-stream/tv/raw/master/BOSS.json",
        "https://gitee.com/xxy002/zhiboyuan/raw/master/dsy",
        "https://iptv.catvod.com/tv.m3u",        
        "https://l.gmbbk.com/upload/39183918.txt",
        "https://live.catvod.com/mq.php?catvod.com=m3u",         
        "https://live.zbds.top/tv/iptv4.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/alantang1977/iptv_api/refs/heads/main/output/live_ipv4.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/alantang1977/iptv-auto/refs/heads/main/my.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/develop202/migu_video/main/interface.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/fafa002/yf2025/refs/heads/main/yiyifafa.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",        
        "https://gh-proxy.com/https://raw.githubusercontent.com/iptv-org/iptv/gh-pages/countries/cn.m3u",
        "https://gh-proxy.com/https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u",
        "https://gh-proxy.com/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1",
        "https://gh-proxy.com/https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/main/merged_output.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/mymsnn/DailyIPTV/main/outputs/full_validated.m3u",
        "https://gh-proxy.com/https://raw.githubusercontent.com/suxuang/myIPTV/main/ipv4.m3u",
        "https://gh-proxy.com/https://raw.githubusercontent.com/suxuang/myIPTV/main/ipv6.m3u",
        "https://gh-proxy.com/https://raw.githubusercontent.com/vbskycn/iptv/master/tv/iptv4.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/vbskycn/iptv/master/tv/iptv6.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/xzw832/cmys/main/S_CCTV.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/xzw832/cmys/main/S_weishi.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u",
        "https://gh-proxy.com/https://raw.githubusercontent.com/yuanzl77/IPTV/master/live.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/zxmlxw520/5566/refs/heads/main/cjdszb.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/zxmlxw520/5566/refs/heads/main/gqds+.txt",
        "https://www.iyouhun.com/tv/myIPTV/ipv4.m3u",
        "https://www.iyouhun.com/tv/myIPTV/ipv6.m3u",
        "https://jihulab.com/owen2000wy/owentv/-/raw/main/HP20230319.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/yoursmile66/TVBox/main/live.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/zqhtym/zqhtym.github.io/refs/heads/main/JG.txt",
        "https://gh-proxy.com/https://raw.githubusercontent.com/dxawi/0/main/tvlive.txt",
        "http://1.94.31.214/live/livelite.txt",   
        "https://d.h6room.com/frjzb.txt"
    ]
    
    # 速度等级配置 (bytes/s) - 按从高到低排序
    SPEED_LEVELS = {
        'excellent': 1024 * 1024,  # 1MB/s
        'wonderful': 1024 * 700,   # 700KB/s
        'good': 1024 * 500,        # 500KB/s
        'useful': 1024 * 200       # 200KB/s
    }
    SPEED_LEVEL_ORDER = ['excellent', 'wonderful', 'good', 'useful']
    
    '''    
    # 分类正则配置
    CATEGORY_PATTERNS = {
        '央视': re.compile(r'cctv|央视|中国中央电视台', re.I),
        '卫视': re.compile(r'卫视', re.I),
        '港澳台': re.compile(r'凤凰|无线|明珠|环球|美亚|翡翠|台视|中视|华视|中天|亚洲', re.I),
        '欧美': re.compile(r'^(?!.*unknow).*(al|ABC|BBC|Bloom|CBS|City|FOX|GB|go2|NBC|News|NTD|UN|Yah|trt|Hollywood)', re.I),
        '其它': re.compile(r'4K|电影|四川|成都|上海|江苏|南京|新闻|高清|1080p', re.I)
    }   
    '''
    # 分类正则配置（新增：排除非中英字符、排除geo-block/persian/firefox）
    CATEGORY_PATTERNS = {
        # 央视：匹配关键词 + 排除非中英字符 + 排除指定敏感词
        '央视': re.compile(r'cctv|央视|中国中央电视台', re.I),
        # 卫视：匹配关键词 + 排除非中英字符 + 排除指定敏感词
        '卫视': re.compile(r'卫视', re.I),
        # 港澳台：匹配关键词 + 排除非中英字符 + 排除指定敏感词
        '港澳台': re.compile(r'凤凰|无线|明珠|环球|美亚|翡翠|台视|中视|华视|中天|亚洲', re.I),
        # 欧美：排除unknown + 匹配关键词 + 排除非中英字符 + 排除指定敏感词
        #'欧美': re.compile(r'^(?!.*(unknown|geo-block|persian|firefox))[\u4e00-\u9fff0-9a-zA-Z\s\(\)\-_\.!]+(al|ABC|BBC|Bloom|CBS|City|FOX|GB|go2|NBC|News|NTD|UN|Yah|trt|Hollywood)[\u4e00-\u9fffa-zA-Z0-9\s\(\)\-_\.!]+$', re.I),
        '欧美': re.compile( r'^(Camp Spoopy|ABC|BBC|Bloomberg|CBS|City|FOX|LiveNOW|GB|Go2|NBC|News|NTD|UN|Yahoo|Real)', re.IGNORECASE),
        # 其它：匹配关键词 + 排除非中英字符 + 排除指定敏感词
        '其它': re.compile(r'4K|电影|四川|成都|上海|江苏|南京|新闻|高清|1080p', re.I)
    }
  
    # 画质正则配置
    QUALITY_PATTERNS = {
        '4D/超高清': re.compile(r'4k|4d|超高清|uhd', re.I),
        '高清/HD': re.compile(r'高清|hd|1080p', re.I),
        'SD': re.compile(r'.*')
    }
    
    # 输出路径
    OUTPUT_DIR = r'C:\exe\m3u-tester-master\DG'
    # 超时配置
    TIMEOUT = {
        'remote_fetch': 10,
        '404_check': 3,
        'speed_test': 5,
        'stream_read': 5,
        'video_check': 15,  # 画面检测超时（秒）
        'video_total_timeout': 180  # 画面检测总超时（3分钟=180秒）
    }
    # 多进程配置（优化：减少进程数以节省内存）
    MULTIPROCESS = {
        '404_processes': max(4, multiprocessing.cpu_count() // 2),  # 减少进程数
        'speed_processes': max(3, multiprocessing.cpu_count() // 3),   # 减少进程数
        'max_total_time': 1800
    }
    # 请求头
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    # 测速配置
    CHUNK_SIZE = 10240  # 10KB  4096
    # 支持的视频流后缀（跳过m3u8解析）
    VIDEO_SUFFIXES = ('.flv', '.mp4', '.ts', '.mkv', '.avi', '.mov')
    
    # 画面检测配置
    VIDEO_CHECK = {
        'frame_interval': 2,  # 每隔2秒取一帧
        'min_diff': 5000,     # 帧差异阈值（低于此值视为画面无变化）
        'min_width': 320,     # 最小有效宽度
        'min_height': 240,    # 最小有效高度
        'audio_check': True   # 是否检测音频
    }

# ======================== 数据模型模块 ========================
class StreamItem:
    """直播流数据模型"""
    def __init__(self, name, url):
        self.name = self._clean_text(name.strip())
        self.url = url.strip()
        self.speed = -1
        self.category = self._get_category()
        self.quality = self._get_quality()
        self.passed_404 = False
        self.speed_level = None
        self.test_duration = 0
        self.error_info = None
        self.is_whitelist = False  # 白名单标记
    
    def _clean_text(self, text):
        """清理文本，移除特殊字符"""
        if not text:
            return text
        # 移除可能导致编码问题的字符
        cleaned = re.sub(r'[^\x00-\x7F\u4e00-\u9FFF\u3000-\u303F\uFF00-\uFFEF]', '', text)
        return cleaned

    def _get_category(self):
        """获取分类"""
        for cat_name, pattern in Config.CATEGORY_PATTERNS.items():
            if pattern.search(self.name):
                return cat_name
    #    if self.url.lower().endswith('.mp4'):   #(Config.VIDEO_SUFFIXES)
    #        return '其它'
        return None

    def _get_quality(self):
        """获取画质"""
        for q_name, pattern in Config.QUALITY_PATTERNS.items():
            if pattern.search(self.name):
                return q_name
        return 'SD'
    
    def _set_speed_level(self):
        """设置速度等级"""
        if self.speed <= 0:
            self.speed_level = None
            return
        
        # 白名单条目最低为useful等级
        if self.is_whitelist:
            for level in Config.SPEED_LEVEL_ORDER:
                if self.speed > Config.SPEED_LEVELS[level]:
                    self.speed_level = level
                    return
            # 如果速度低于所有等级阈值，白名单条目设为useful
            self.speed_level = 'useful'
            return
        
        # 普通条目按正常逻辑
        for level in Config.SPEED_LEVEL_ORDER:
            if self.speed > Config.SPEED_LEVELS[level]:
                self.speed_level = level
                return
        self.speed_level = None

    def __repr__(self):
        return f"<StreamItem {self.name} | {self.speed} bytes/s | 等级: {self.speed_level}>"

# ======================== 工具函数模块 ========================
def get_beijing_time(fmt='%Y%m%d%H%M'):
    """获取北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz).strftime(fmt)

def ensure_dir(dir_path):
    """确保目录存在"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def safe_decode(byte_data):
    """安全解码：优先utf-8，失败则用gbk，最后用ignore"""
    try:
        return byte_data.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return byte_data.decode('gbk')
        except UnicodeDecodeError:
            return byte_data.decode('utf-8', errors='ignore')
        
# 全局变量用于超时控制
timeout_flag = False
def timeout_handler():
    """超时回调函数"""
    global timeout_flag
    timeout_flag = True

def check_ffmpeg():
    """检查FFmpeg是否可用"""
    if shutil.which('ffmpeg'):
        return True
    # 尝试常见路径
    ffmpeg_paths = [
        r'H:\11 tool\装机\视频\哔哩下载姬（downkyi）-27-1.3.4\ffmpeg.exe',
        r'C:\Users\Administrator\AppData\Roaming\anythingllm-desktop\storage\engines\ffmpeg\windows-x64\ffmpeg.exe',
        r'C:\Program Files\iGameCenter\SAVIConverter\tools\ffmpeg.exe',
        r'C:\Users\Administrator\AppData\Local\Programs\icat\resources\bin\ffmpeg\ffmpeg.exe'
    ]
    for path in ffmpeg_paths:
        if os.path.exists(path):
            os.environ['PATH'] += os.pathsep + os.path.dirname(path)
            return True
    return False        

# ======================== Step1: 初始化模块 ========================
def init():
    """初始化环境"""
    print("="*80)
    print(f"【Step1: 初始化】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    
    # Windows多进程修复
    if sys.platform == 'win32':
        multiprocessing.freeze_support()
    
    # 检查依赖
    dependencies = {
        'pytz': 'pytz',
        'cv2': 'opencv-python',
        'pymediainfo': 'pymediainfo'
    }
    for pkg, install_name in dependencies.items():
        try:
            __import__(pkg)
        except ImportError:
            print(f"安装依赖库{install_name}...")
            os.system(f'pip install {install_name} -i https://pypi.tuna.tsinghua.edu.cn/simple')
            __import__(pkg)
        
    # 检查FFmpeg
    if not check_ffmpeg():
        print("⚠️  未找到FFmpeg，画面检测功能可能受限！请安装FFmpeg并添加到环境变量")
    
    ensure_dir(Config.OUTPUT_DIR)
    
    start_time = time.perf_counter()
    return {
        'start_time': start_time,
        'daytime': get_beijing_time(),
        'manager': Manager()
    }

# ======================== Step2: 资源读取模块 ========================
def load_resources():
    """读取所有资源"""
    print("\n" + "="*80)
    print(f"【Step2: 读取资源】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    
    all_items = []
    # 读取白名单
    whitelist = _load_whitelist()
    # 读取本地M3U
    local_items = _load_local_m3u(whitelist)
    all_items.extend(local_items)
    print(f"本地M3U读取完成，共 {len(local_items)} 条")
    # 读取本地txt
    local_items = _load_local_txt(whitelist)
    all_items.extend(local_items)
    print(f"本地txt文件读取完成，共 {len(local_items)} 条")
    
    # 读取远程资源
    remote_items = _load_remote_resources(whitelist)
    all_items.extend(remote_items)
    print(f"远程资源读取完成，共 {len(remote_items)} 条")
    
    print(f"【Step2: 读取资源】总计读取 {len(all_items)} 条原始数据")
    return all_items

def _load_whitelist():
    """读取白名单文件"""
    whitelist = set()
    filename = "white.txt"
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and ',' in line and '#' not in line:
                        parts = line.split(',', 1)  # 只分割第一个逗号（避免URL含逗号）
                        if len(parts) == 2:
                            name = parts[0].strip() or '未知'
                            url = parts[1].strip()
                            if name and url and url.startswith('http'):  # URL非空才添加
                                
                                # 支持URL和名称匹配
                                whitelist.add(url)
            print(f"成功读取白名单 {filename}，共 {len(whitelist)} 条")
        except Exception as e:
            print(f"读取白名单文件 {filename} 失败: {e}")
    else:
        print(f"未找到白名单文件 {filename}，跳过白名单读取")
    return whitelist


def _load_local_m3u(whitelist):
    """读取本地M3U文件"""
    local_items = []
    # 只读取resources.m3u文件
    filename = "resources.m3u"
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                extinf = ''
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('#EXTINF'):
                        extinf = line
                    elif extinf and not line.startswith('#'):
                        name = extinf.split(',')[-1].strip() if ',' in extinf else '未知'
                        item = StreamItem(name, line)
                        # 检查是否在白名单中
                        if name in whitelist or line in whitelist:
                            item.is_whitelist = True
                        local_items.append(item)
                        extinf = ''
            print(f"成功读取 {filename}")
        except Exception as e:
            print(f"读取本地文件 {filename} 失败: {e}")
    else:
        print(f"未找到 {filename} 文件，跳过M3U读取")
    return local_items

def _load_local_txt(whitelist):
    """
    读取本地TXT文件中的电视名和URL
    支持两种格式：
    1. 逗号分隔：安徽卫视 HD,http://xxx.xxx.xxx
    2. 脱字符分隔：广西卫视^https://xxx.xxx^卫视^SD^xxx^excellent
    """
    local_items = []
    # 只读取resources.txt文件
    filenames = ["resources.txt","white.txt"]
    for filename in filenames:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        # 跳过空行和注释行
                        if not line or line.startswith('#'):
                            continue
                        
                        # ========== 格式1：逗号分隔（名称,URL） ==========
                        if ',' in line and '^' not in line:
                            parts = line.split(',', 1)  # 只分割第一个逗号（避免URL含逗号）
                            if len(parts) == 2:
                                name = parts[0].strip() or '未知'
                                url = parts[1].strip()
                                if url:  # URL非空才添加
                                    item = StreamItem(name, url)
                                    # 检查是否在白名单中
                                    if url in whitelist:
                                        item.is_whitelist = True
                                    local_items.append(item)
                        
                        # ========== 格式2：脱字符分隔（名称^URL^分类^画质^...） ==========
                        elif '^' in line:
                            parts = line.split('^')
                            if len(parts) >= 2:  # 至少包含名称和URL
                                name = parts[0].strip() or '未知'
                                url = parts[1].strip()
                                if url:  # URL非空才添加
                                    item = StreamItem(name, url)
                                    # 检查是否在白名单中
                                    if url in whitelist:
                                        item.is_whitelist = True
                                    local_items.append(item)
                        
                        # 其他格式跳过（避免无效数据）
                        else:
                            continue
                print(f"成功读取 {filename}")
            except Exception as e:
                print(f"读取本地文件 {filename} 失败: {e}")
        else:
            print(f"未找到 {filename} 文件，跳过TXT读取")
    return local_items

def _load_remote_resources(whitelist):
    """读取远程资源"""
    remote_items = []
    for url in Config.REMOTE_URLS:
        print(f"正在获取远程资源: {url}")
        try:
            req = Request(url, headers=Config.HEADERS)
            resp = urlopen(req, timeout=Config.TIMEOUT['remote_fetch'])
            
            if resp.getcode() == 404:
                print(f"资源不存在(404): {url}")
                continue
            
            content = resp.read().decode('utf-8', errors='ignore').splitlines()
            extinf = ''
            for line in content:
                line = line.strip()
                if not line or line.startswith('#EXTM3U') or line == '#genre#':
                    continue
                
                if ',' in line and not line.startswith('#'):
                    parts = line.split(',', 1)
                    if len(parts) == 2 and parts[1].strip():
                        name = parts[0]
                        stream_url = parts[1]
                        item = StreamItem(name, stream_url)
                        # 检查是否在白名单中
                        if stream_url in whitelist:
                            item.is_whitelist = True
                        remote_items.append(item)
                elif line.startswith('#EXTINF'):
                    extinf = line
                elif extinf:
                    name = extinf.split(',')[-1].strip() if ',' in extinf else '未知'
                    item = StreamItem(name, line)
                    # 检查是否在白名单中
                    if line in whitelist:
                        item.is_whitelist = True
                    remote_items.append(item)
                    extinf = ''
        except (HTTPError, URLError) as e:
            print(f"获取远程资源 {url} 失败: {e}")
        except Exception as e:
            print(f"处理远程资源 {url} 出错: {e}")
    return remote_items

# ======================== Step3: URL去重模块 ========================
def deduplicate_items(items):
    """URL去重"""
    print("\n" + "="*80)
    print(f"【Step3: URL去重】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    
    url_map = {}
    for item in items:
        if not item.url:
            continue
        if item.url in url_map:
            existing = url_map[item.url]
            if len(item.name) > len(existing.name) and item.name != '未知':
                url_map[item.url] = item
        else:
            url_map[item.url] = item
    
    deduplicated = list(url_map.values())
    print(f"【Step3: URL去重】完成，原始 {len(items)} 条 → 去重后 {len(deduplicated)} 条")
    return deduplicated

# ======================== Step4: 名称/URL筛查模块 ========================
def filter_items(items):
    """名称/URL筛查"""
    print("\n" + "="*80)
    print(f"【Step4: 名称/URL筛查】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    
    filtered = [item for item in items if item.category is not None or item.is_whitelist]
    print(f"【Step4: 名称/URL筛查】完成，去重后 {len(items)} 条 → 筛查后 {len(filtered)} 条")
    return filtered

# ======================== Step5: 多进程404筛查模块 ========================
def _check_404_worker(item, progress_dict):
    """404筛查工作进程"""
    try:
        # 使用GET请求替代HEAD，提高兼容性
        req = Request(item.url, headers=Config.HEADERS)
        with urlopen(req, timeout=Config.TIMEOUT['404_check']) as resp:
            # 检查响应状态码
            if resp.getcode() == 200:
                item.passed_404 = True
            else:
                item.passed_404 = resp.getcode() != 404
    except HTTPError as e:
        if e.code == 404:
            item.passed_404 = False
        else:
            item.passed_404 = True
    except (URLError, TimeoutError, Exception):
        item.passed_404 = True
    
    progress_dict['processed'] += 1
    processed = progress_dict['processed']
    total = progress_dict['total']
    if processed % 10 == 0:
        print(f"\r404检测进度：{processed}/{total}", end='', flush=True)
    
    return item

def check_404(items):
    """多进程404筛查"""
    print("\n" + "="*80)
    print(f"【Step5: 404筛查】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    print(f"启动 {Config.MULTIPROCESS['404_processes']} 个进程进行404检测...")
    
    total = len(items)
    if total == 0:
        print("无条目需要检测404")
        return []
    
    manager = Manager()
    progress_dict = manager.dict()
    progress_dict['processed'] = 0
    progress_dict['total'] = total
    
    result = []
    try:
        with ProcessPoolExecutor(max_workers=Config.MULTIPROCESS['404_processes']) as executor:
            futures = []
            worker_func = partial(_check_404_worker, progress_dict=progress_dict)
            for item in items:
                futures.append(executor.submit(worker_func, item))
            
            for future in futures:
                try:
                    res = future.result(timeout=Config.MULTIPROCESS['max_total_time'])
                    result.append(res)
                except FutureTimeoutError:
                    print(f"\n404检测超时，强制终止")
                    executor.shutdown(wait=False, cancel_futures=True)
                    return []
                except Exception as e:
                    print(f"\n单个404检测任务出错: {e}")
                    continue
                    
    except Exception as e:
        print(f"\n404检测进程池出错: {e}")
        return []
    
    valid_items = [item for item in result if item.passed_404]
    print(f"\n【Step5: 404筛查】完成，筛查前 {total} 条 → 通过 {len(valid_items)} 条")
    return valid_items

# ======================== Step6: 多进程速度筛查模块（修复编码错误+恢复多进程） ========================
class Downloader:
    """测速类"""
    def __init__(self, url):
        self.url = url
        self.startTime = time.time()
        self.recive = 0
        self.endTime = None

    def getSpeed(self):
        """计算速度（bytes/s）"""
        if self.endTime and self.recive != -1 and (self.endTime - self.startTime) > 0:
            return self.recive / (self.endTime - self.startTime)
        else:
            return -1

def getStreamUrl(m3u8: str, depth: int = 1):
    
    """解析 M3U8 流地址（优化：递归深度限制+超时控制+快速失败）"""
    MAX_RECURSION_DEPTH = 2
    urls = []
    # 递归深度限制，避免无限嵌套
    if depth > MAX_RECURSION_DEPTH:
        print(f'⚠️  递归深度超过限制（{MAX_RECURSION_DEPTH}层），跳过：{m3u8}')
        return urls
    try:
        # 构建请求，添加超时和User-Agent（避免被服务器拒绝）
        req = Request(m3u8, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=5) as resp:
            prefix = ''
            # 提取基础路径（优化：处理无 '/' 的本地路径）
            if '/' in m3u8:
                prefix = m3u8[:m3u8.rindex('/') + 1]
            
            firstLine = True
            top = False  # 标记需要递归解析的嵌套M3U8
            second = False  # 标记直接流地址
            lines_processed = 0
            max_lines = 100  # 限制最大处理行数，避免超大文件阻塞
            for line in resp:
                lines_processed += 1
                if lines_processed > max_lines:
                    print(f'⚠️  M3U8 文件行数过多（超过{max_lines}行），跳过剩余内容：{m3u8}')
                    break
                line = line.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                # 快速判断：非M3U文件直接返回原地址
                if firstLine:
                    if line != '#EXTM3U':
                        urls.append(m3u8)
                        break
                    firstLine = False
                    continue
                # 处理嵌套M3U8（递归）
                if top:
                    if not line.lower().startswith('http'):
                        line = prefix + line
                    # 递归解析，深度+1
                    nested_urls = getStreamUrl(line, depth + 1)
                    urls.extend(nested_urls)
                    top = False
                # 处理直接流地址
                elif second:
                    if not line.lower().startswith('http'):
                        line = prefix + line
                    urls.append(line)
                    second = False
                # 标记状态
                elif line.startswith('#EXT-X-STREAM-INF:'):
                    top = True
                elif line.startswith('#EXTINF:'):
                    second = True
            # 去重，避免重复测试相同流地址
            urls = list(dict.fromkeys(urls))[:3]  # 最多保留3个流地址，避免过多测试
    except Exception as e:
        error_msg = str(e)
        # 简化错误提示，避免冗余
        if 'timeout' in error_msg.lower():
            print(f'❌ 解析 {m3u8} 超时（{5}秒）')
        else:
            print(f'❌ 解析 {m3u8} 失败：{error_msg[:50]}...')  # 截断过长错误信息
    return urls   
    
    
 
def downloadTester(downloader: Downloader):
    """下载测速"""
    chunck_size = Config.CHUNK_SIZE
    
    """测速函数优化（严格超时控制+快速退出）"""
    try:
        req = Request(downloader.url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=5) as resp:
            # 严格控制测速时间，超时直接退出
            while time.time() - downloader.startTime < 3:
                chunk = resp.read(chunck_size)
                if not chunk:
                    break  # 数据读取完毕，提前退出
                downloader.recive += len(chunk)
                # 每读取10块检查一次时间，避免阻塞
                if downloader.recive // chunck_size >= 10:
                    if time.time() - downloader.startTime >= 3:
                        break
    except Exception as e:
        error_msg = str(e)
        if 'timeout' in error_msg.lower():
            print(f'⚠️  测速超时（{3}秒）：{downloader.url}')
        else:
            print(f'⚠️  测速失败：{downloader.url} - {error_msg[:30]}...')
        downloader.recive = -1
    finally:
        downloader.endTime = time.time()
    
    








def _test_speed_worker(item, progress_dict):
    """速度测试工作进程"""
    
    if item.is_whitelist:
        item.speed = 220000
        item.speed_level = "useful"
        
    try:
        # 解析流地址
        stream_urls = []
        if item.url.lower().endswith(Config.VIDEO_SUFFIXES):
            stream_urls.append(item.url)
        else:
            stream_urls = getStreamUrl(item.url)
        
        if not stream_urls:
            raise Exception('未解析到有效流地址')
        
        # 测试第一个流地址
        downloader = Downloader(stream_urls[0])
        downloadTester(downloader)
        if downloader.getSpeed()>220000:
            item.speed = downloader.getSpeed()
            item._set_speed_level()
        
    except Exception as e:
        if not item.is_whitelist:
            item.speed = -1
            item.speed_level = None
            item.error_info = str(e)
    
    progress_dict['processed'] += 1
    processed = progress_dict['processed']
    total = progress_dict['total']
    if processed % 10 == 0:
        print(f"\r速度测试进度：{processed}/{total}", end='', flush=True)
    
    return item

def test_speed(items):
    """多进程速度测试"""
    print("\n" + "="*80)
    print(f"【Step6: 速度筛查】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    print(f"启动 {Config.MULTIPROCESS['speed_processes']} 个进程进行速度测试...")
    
    total = len(items)
    if total == 0:
        print("无条目需要测试速度")
        return []
    
    manager = Manager()
    progress_dict = manager.dict()
    progress_dict['processed'] = 0
    progress_dict['total'] = total
    
    result = []
    try:
        with ProcessPoolExecutor(max_workers=Config.MULTIPROCESS['speed_processes']) as executor:
            futures = []
            worker_func = partial(_test_speed_worker, progress_dict=progress_dict)
            for item in items:
                futures.append(executor.submit(worker_func, item))
            
            for future in futures:
                try:
                    res = future.result(timeout=Config.MULTIPROCESS['max_total_time'])
                    result.append(res)
                except FutureTimeoutError:
                    print(f"\n速度测试超时，强制终止")
                    executor.shutdown(wait=False, cancel_futures=True)
                    return []
                except Exception as e:
                    print(f"\n单个速度测试任务出错: {e}")
                    continue
                    
    except Exception as e:
        print(f"\n速度测试进程池出错: {e}")
        return []
    
    # 统计结果
    success_count = len([item for item in result if item.speed > 0])
    level_count = {l:0 for l in Config.SPEED_LEVEL_ORDER}
    
    for item in result:
        if item.speed_level:
            level_count[item.speed_level] += 1
    
    level_summary = []
    total_valid = sum(level_count.values())
    for level in Config.SPEED_LEVEL_ORDER:
        count = level_count[level]
        ratio = f"{(count/total_valid)*100:.1f}%" if total_valid > 0 else "0.0%"
        level_summary.append(f"{level}: {count} 条（{ratio}）")
    level_summary_str = ' | '.join(level_summary)
    
    print(f"\n【Step6: 速度筛查】完成，总计测速 {total} 条 → 有效测速 {success_count} 条")
    print(f"【速度等级统计】{level_summary_str} | 测速失败：{total - success_count} 条")
    
    return result        


# ======================== Step9: 画面有效性检测模块（新增） ========================
def analyze_media_info(url):
    """分析媒体信息（音频/视频轨道）- 带超时控制"""
    import signal
    import threading
    
    # 超时处理函数
    def timeout_handler(signum, frame):
        raise TimeoutError("MediaInfo分析超时")
    
    # 创建一个带超时的执行函数
    def run_with_timeout(func, timeout_seconds):
        """在单独线程中执行函数，带超时控制"""
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
            # 线程仍在运行，说明超时了
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
    避免pymediainfo版本兼容问题 - 带超时控制
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
            return has_video, False  # 返回已检测到的视频结果
        
        has_audio = 'audio' in result_audio.stdout.lower()
        
        return has_video, has_audio
    
    except Exception as e:
        print(f"[调试] FFmpeg媒体分析失败 | URL: {url} | 错误: {e}")
        return False, False

'''
def check_video_changes(url):
    """检测15秒内画面是否变化（新增404前置检测+无效URL容错）"""
    
    
    global timeout_flag
    timeout_flag = False  # 重置超时标记
    
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
                print(f"[调试] 画面变化检测失败 | URL: {url} | 错误: 404 Not Found（链接无效）")
                return False
            url_valid = True  # 非404错误（如500）仍尝试读取
        except (URLError, TimeoutError):
            print(f"[调试] 画面变化检测失败 | URL: {url} | 错误: 无法连接（网络超时/链接不可达）")
            return False
        
        if not url_valid:
            return False
        
        # 前置步骤2：判断是否为ts片段（避免单一片段无法播放）
        url_lower = url.lower()
        if url_lower.endswith('.ts'):
            print(f"[调试] 检测到TS单一片段 | URL: {url} | 提示：TS片段需通过m3u8索引播放，单独无法解析画面")
            return False
        
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
                print(f"[调试] 画面变化检测失败 | URL: {url} | 错误: 无法打开视频流（格式不支持/链接无效）")
                cap.release()
                return False
            
        # 3. 读取帧并检测变化（带超时检查）
        frames = []
        start_time = time.time()
        last_frame_time = start_time
        frame_read_count = 0  # 统计成功读取的帧数
        
        while time.time() - start_time < Config.TIMEOUT['video_check']:
            # 检查是否超时（3分钟）
            if timeout_flag:
                print(f"[调试] 画面检测超时 | URL: {url} | 原因: 超过3分钟强制终止")
                cap.release()
                return False
            
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
            print(f"[调试] 画面变化检测失败 | URL: {url} | 错误: 未读取到任何视频帧（可能是无效流/格式不支持）")
            return False
        
        if len(frames) < 2:
            print(f"[调试] 画面变化检测失败 | URL: {url} | 错误: 有效帧数不足（共读取{frame_read_count}帧，需至少2帧对比）")
            return False
        
        # 计算相邻帧差异
        total_diff = 0
        for i in range(1, len(frames)):
            diff = cv2.absdiff(frames[i-1], frames[i])
            non_zero = np.count_nonzero(diff)
            total_diff += non_zero
        
        avg_diff = total_diff / (len(frames) - 1)
        is_changing = avg_diff > Config.VIDEO_CHECK['min_diff']
        
        print(f"[调试] 画面变化检测成功 | URL: {url} | 读取帧数: {frame_read_count} | 有效对比帧数: {len(frames)} | 平均帧差异: {avg_diff:.0f} | 变化: {is_changing}")
        return is_changing
    
    except Exception as e:
        # 异常时检查是否超时
        if timeout_flag:
            print(f"[调试] 画面检测超时 | URL: {url} | 原因: 超过3分钟强制终止")
        else:
            print(f"[调试] 画面变化检测异常 | URL: {url} | 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 停止定时器（避免内存泄漏）
        timer.cancel()
'''
def check_video_changes(url):
    """
    检测画面变化（进程级3分钟超时）
    自动检测环境并选择合适的检测策略
    :param url: 视频流URL
    :return: True=画面变化，False=无变化/超时/失败
    """
    # 1. 检测运行环境并选择合适的worker脚本
    is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    
    if is_github_actions:
        worker_script = os.path.join(os.path.dirname(__file__), 'video_check_worker_github.py')
        print(f"[环境检测] 使用GitHub Actions优化版本 | URL: {url}")
    else:
        worker_script = os.path.join(os.path.dirname(__file__), 'video_check_worker.py')
        print(f"[环境检测] 使用标准版本 | URL: {url}")
    
    # 如果GitHub Actions版本不存在，回退到自动版本
    if not os.path.exists(worker_script):
        worker_script = os.path.join(os.path.dirname(__file__), 'video_check_worker_auto.py')
        print(f"[环境检测] 回退到自动版本 | URL: {url}")
    
    if not os.path.exists(worker_script):
        print(f"[调试] 画面检测失败 | URL: {url} | 错误: 找不到worker脚本 {worker_script}")
        return False
    
    # 2. 启动子进程执行检测（设置3分钟超时）
    try:
        # 构建命令
        cmd = [sys.executable, worker_script, url]
        
        # 执行并设置180秒（3分钟）超时
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 核心：3分钟超时
            encoding='utf-8'
        )
        
        # 3. 解析结果（适配新的JSON返回结构）
        if result.returncode != 0:
            print(f"[调试] 画面检测失败 | URL: {url} | 错误: 子进程执行失败 | 错误输出: {result.stderr.strip()}")
            return False
        
        # 清理输出（去除可能的调试日志，只保留最后一行JSON）
        stdout_lines = result.stdout.strip().split('\n')
        
        json_lines = []
        in_json = False  # 标记是否进入JSON块
        for line in stdout_lines:
            stripped_line = line.strip()
            # 检测JSON开始/结束标记
            if stripped_line == '{':
                in_json = True
                json_lines.append(stripped_line)
            elif stripped_line == '}':
                in_json = False
                json_lines.append(stripped_line)
            elif in_json:
                json_lines.append(stripped_line)
                
        json_str = '\n'.join(json_lines)
        
        if not json_str:
            print(f"[调试] 画面检测失败 | URL: {url} | 错误: 未找到有效JSON结果 | 原始输出: {result.stdout}")
            return False
        
        try:
            res_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[调试] 画面检测失败 | URL: {url} | 错误: 解析JSON失败 | 错误信息: {str(e)} | JSON内容: {json_str}")
            return False
        
        # 4. 处理新结构的返回结果
        # 提取核心字段（兼容新返回值结构）
        success = res_data.get('success', False)
        changing = res_data.get('changing', False)
        reason = res_data.get('reason', 'unknown')
        frame_info = res_data.get('frame_info', {})
        
        # 解析帧信息
        total_read = frame_info.get('total_read', 0)
        valid_frames = frame_info.get('valid_frames', 0)
        avg_diff = frame_info.get('avg_diff', 0.0)
        
        # 5. 结果判断逻辑
        if not success:
            print(f"[调试] 画面检测失败 | URL: {url} | 原因: {reason}")
            return False
        
        # 检测成功，输出详细信息
        print(f"[调试] 画面检测完成 | URL: {url} ")
        print(f"       ├── 总读取帧数: {total_read} | 有效对比帧数: {valid_frames}")
        print(f"       ├── 平均帧差异: {avg_diff:.2f} | 画面变化: {changing}")
        
        return changing
    
    except subprocess.TimeoutExpired:
        # 核心：3分钟超时触发
        print(f"[调试] 画面检测超时 | URL: {url} | 原因: 超过3分钟强制终止子进程")
        return False
    
    except Exception as e:
        print(f"[调试] 画面检测异常 | URL: {url} | 错误类型: {type(e).__name__} | 错误信息: {str(e)}")

def _video_check_worker(item):
    """视频检测工作线程"""
    # 白名单检查：跳过画面检测
    if item.is_whitelist:
        print(f"[白名单] 跳过画面检测 | 名称: {item.name} | URL: {item.url}")
        # 白名单条目直接标记为视频有效
        item.video_valid = True
        item.has_video = True
        item.has_audio = True
        item.video_changing = True
        return item, "whitelist"
    
    # 旧的白名单检查逻辑（保留兼容性）
    is_whitelisted = False
    whitelist_reason = ""
    
    # 检查特定IP地址
    if "8.218.84.3:8885" in item.url:
        is_whitelisted = True
        whitelist_reason = "白名单IP地址"
    # 检查特定文件格式
    elif item.url.lower().endswith(('.mp4', '.flv')):
        is_whitelisted = True
        whitelist_reason = "白名单文件格式"
    
    if is_whitelisted:
        # 白名单条目直接标记为视频有效
        item.video_valid = True
        item.has_video = True
        item.has_audio = True
        item.video_changing = True
        return item, "whitelist"
    '''
    # 添加跳过机制：对于速度较低的条目跳过画面检测
    if item.speed < 1024 * 100:  # 速度低于100KB/s的跳过
        item.video_valid = False
        item.has_video = False
        item.has_audio = False
        item.video_changing = False
        return item, "skip"
    '''
    # 执行视频检测
    url_start_time = time.time()
    timeout_occurred = False
    
    try:
        # 检查是否已经超时（在解析前先检查）
        if time.time() - url_start_time > 180:
            item.video_valid = False
            return item, "timeout"
        
        # 解析真实流地址（带超时检查）
        stream_urls = getStreamUrl(item.url)
        
        # 检查解析是否超时
        if time.time() - url_start_time > 180:
            item.video_valid = False
            return item, "timeout"
            
        if not stream_urls:
            item.video_valid = False
            return item, "no_stream"
        
        stream_url = stream_urls[0]
        
        # 检查是否已经超时（在媒体信息检测前）
        if time.time() - url_start_time > 180:
            item.video_valid = False
            return item, "timeout"
        
        # 媒体信息检测
        has_video, has_audio = analyze_media_info(stream_url)
        item.has_video = has_video
        item.has_audio = has_audio
        
        # 检查是否已经超时（在画面变化检测前）
        if time.time() - url_start_time > 180:
            item.video_valid = False
            return item, "timeout"
        
        # 画面变化检测
        video_changing = check_video_changes(item.url)  #stream_url  改为item.url
        item.video_changing = video_changing
        
        # 最终判断
        if has_video and has_audio and video_changing:
            item.video_valid = True
            return item, "valid"
        else:
            item.video_valid = False
            return item, "invalid"
            
    except Exception as e:
        total_url_time = time.time() - url_start_time
        if total_url_time > 180:
            return item, "timeout"
        else:
            return item, "error"

def check_video_validity(items, max_threads=4):
    """批量检测视频有效性（多线程版本）"""
    print("\n" + "="*80)
    print(f"【Step9: 画面有效性检测】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    print(f"检测规则：1.有声音+有画面 2.15秒内画面内容变化")
    print(f"超时控制：每个URL检测最多3分钟，超时自动中止并进入下一个")
    print(f"多线程：使用 {max_threads} 个线程并发检测")
    
    total = len(items)
    if total == 0:
        print("无条目需要检测视频有效性")
        return []
    
    processed = 0
    valid_count = 0
    timeout_count = 0
    skip_count = 0
    whitelist_count = 0
    result = []
    
    # 使用线程池进行并发检测
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        # 提交所有任务
        future_to_item = {executor.submit(_video_check_worker, item): item for item in items}
        
        # 处理完成的任务
        for future in as_completed(future_to_item):
            processed += 1
            item = future_to_item[future]
            
            try:
                processed_item, status = future.result(timeout=200)  # 200秒超时
                
                # 根据状态更新统计
                if status == "whitelist":
                    whitelist_count += 1
                    print(f"[{processed}/{total}] 白名单跳过 | 名称: {item.name}")
                elif status == "skip":
                    skip_count += 1
                    print(f"[{processed}/{total}] 跳过低速 | 名称: {item.name}")
                elif status == "valid":
                    valid_count += 1
                    print(f"[{processed}/{total}] 检测完成 | 名称: {item.name} | 有效")
                elif status == "timeout":
                    timeout_count += 1
                    print(f"[{processed}/{total}] 检测超时 | 名称: {item.name}")
                elif status == "error":
                    print(f"[{processed}/{total}] 检测异常 | 名称: {item.name}")
                else:
                    print(f"[{processed}/{total}] 检测无效 | 名称: {item.name}")
                
                result.append(processed_item)
                
                # 显示进度
                remaining = total - processed
                print(f"进度：{processed}/{total} | 剩余：{remaining} | 有效: {valid_count} | 白名单: {whitelist_count} | 跳过: {skip_count} | 超时: {timeout_count}")
                
            except Exception as e:
                print(f"[{processed}/{total}] 线程异常 | 名称: {item.name} | 错误: {e}")
                item.video_valid = False
                result.append(item)
    
    # 过滤无效视频
    valid_items = [item for item in result if item.video_valid]
    print(f"\n【Step9: 画面有效性检测】完成，总计检测 {total} 条 → 有效视频 {valid_count} 条")
    print(f"【过滤结果】原始 {total} 条 → 有效 {len(valid_items)} 条 | 白名单跳过: {whitelist_count} 条 | 跳过低速: {skip_count} 条 | 超时中止: {timeout_count} 条")
    
    return valid_items


# ======================== Step10: 结果整理模块（央视数字排序） ========================
def organize_results(items):
    """
    结果整理（核心优化：央视条目按数字升序排列，如CCTV1→CCTV2→...→CCTV9→CCTV10）
    """
    print("\n" + "="*80)
    print(f"【Step10: 结果整理】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    
    # 基础优先级配置
    cat_priority = {'央视':0, '卫视':1, '港澳台':2, '欧美':3, '其它':4}
    quality_priority = {'4D/超高清':0, '高清/HD':1, 'SD':2}
    
    def extract_cctv_number(name):
        """提取央视名称中的数字（用于排序）"""
        name_upper = name.upper()
        match = re.search(r'(CCTV|央视)(\d+)', name_upper)
        if match:
            return int(match.group(2))
        return 999  # 无数字条目排最后
    
    def sort_cctv_items(items):
        """央视条目专用排序：按数字升序，兼顾速度和画质"""
        return sorted(
            items,
            key=lambda x: (
                extract_cctv_number(x.name),  # 核心：数字升序
                -int(x.speed) if isinstance(x.speed, (int, float)) and x.speed > 0 else 0,  # 速度降序，确保是整数
                quality_priority.get(x.quality, 2)  # 画质优先级
            )
        )
    
    def sort_other_items(items):
        """非央视条目排序：卫视、欧美、其它按name排序，相同name按speed排序；港澳台保持原有逻辑"""
        return sorted(
            items,
            key=lambda x: (
                x.name,                    # 主要按名称排序
                -int(x.speed) if isinstance(x.speed, (int, float)) and x.speed > 0 else 0,  # 相同名称按速度降序
                quality_priority.get(x.quality, 2)  # 最后按画质优先级
            )
        )
    
    organized = {}
    for standard in Config.SPEED_LEVEL_ORDER:
        min_speed = Config.SPEED_LEVELS[standard]
        # 确保speed是数字类型再进行比较
        level_items = [item for item in items 
                      if isinstance(item.speed, (int, float)) 
                      and item.speed > min_speed 
                      and item.speed_level == standard]
        if not level_items:
            organized[standard] = []
            continue
        
        # 按分类分组处理排序
        cat_groups = {}
        # 处理央视分类
        cctv_items = [item for item in level_items if item.category == '央视']
        if cctv_items:
            cat_groups['央视'] = sort_cctv_items(cctv_items)
        # 处理其他分类
        for cat in ['卫视', '港澳台', '欧美', '其它']:
            cat_items = [item for item in level_items if item.category == cat]
            if cat_items:
                cat_groups[cat] = sort_other_items(cat_items)
        
        # 合并所有分类
        final_sorted = []
        for cat in cat_priority.keys():
            if cat in cat_groups:
                final_sorted.extend(cat_groups[cat])
        
        organized[standard] = final_sorted
        print(f"【{standard}等级】整理完成，共 {len(final_sorted)} 条（央视条目已按数字升序排列）")
    
    return organized



# ======================== Step8: 结果输出模块 ========================
def export_results(organized_data, daytime):
    """
    结果输出（层级包含规则）：
    - excellent：仅输出excellent等级条目
    - wonderful：输出excellent + wonderful等级条目
    - good：输出excellent + wonderful + good等级条目
    - useful：输出excellent + wonderful + good + useful等级条目
    """
    print("\n" + "="*80)
    print(f"【Step8: 结果输出】开始时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
    ensure_dir(Config.OUTPUT_DIR)
    
    # 定义速度等级的层级顺序（从高到低）
    speed_level_hierarchy = Config.SPEED_LEVEL_ORDER
    
    # 遍历每个目标输出等级
    for target_standard in speed_level_hierarchy:
        # 收集当前等级及所有更高等级的条目
        combined_items = []
        # 找到当前等级在层级中的索引，包含所有索引<=当前的等级
        target_index = speed_level_hierarchy.index(target_standard)
        for level in speed_level_hierarchy[:target_index+1]:
            if level in organized_data and organized_data[level]:
                combined_items.extend(organized_data[level])
        
        # 去重（避免同一条目在多个等级中重复出现）
        # 按URL去重，保留速度最高的条目
        url_map = {}
        for item in combined_items:
            if item.url not in url_map:
                url_map[item.url] = item
            else:
                # 保留速度更高的条目
                if item.speed > url_map[item.url].speed:
                    url_map[item.url] = item
        final_items = list(url_map.values())
        
        if not final_items:
            print(f"【{target_standard}等级】无符合条件条目，跳过输出")
            continue
        
        # 生成输出文件
        filename = f"live+{target_standard}+{daytime}.txt"
        output_path = os.path.join(Config.OUTPUT_DIR, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # 可选：取消注释恢复文件头（如需保留）
            # f.write(f"#EXTM3U\n")
            # f.write(f"# 筛选等级：{target_standard}（包含{'+'.join(speed_level_hierarchy[:target_index+1])}） | 速度阈值：{Config.SPEED_LEVELS[target_standard]/1024:.0f}KB/s\n")
            # f.write(f"# 生成时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')} | 条目总数：{len(final_items)}\n")
            # f.write(f"# 格式：名称,URL\n#\n")
            
            # 按分类排序输出
            cat_order = ['欧美','央视', '卫视', '港澳台',  '其它']
            for cat in cat_order:
                cat_items = [item for item in final_items if item.category == cat]
                if not cat_items:
                    continue
                # 写入分类组
                f.write(f" {cat}（{len(cat_items)}条） ,#group# \n\n")
                
                # 按画质排序输出
                quality_order = ['4D/超高清', '高清/HD', 'SD']
                for q in quality_order:
                    q_items = [item for item in cat_items if item.quality == q]
                    if not q_items:
                        continue
                    # 写入画质组
                    f.write(f"{cat} {q}（{len(q_items)}条） ,#group# \n\n")
                    # 写入具体条目
                    for item in q_items:
                        f.write(f"{item.name},{item.url}\n")
                f.write(f" \n")
        
        # 输出统计信息
        print(f"【输出完成】{target_standard} → {output_path}（共{len(final_items)}条，包含{'+'.join(speed_level_hierarchy[:target_index+1])}等级）")
    
    # 统计有效文件数
    valid_files = 0
    for target_standard in speed_level_hierarchy:
        target_index = speed_level_hierarchy.index(target_standard)
        combined_items = []
        for level in speed_level_hierarchy[:target_index+1]:
            if level in organized_data and organized_data[level]:
                combined_items.extend(organized_data[level])
        if combined_items:
            valid_files += 1
    
    print(f"【Step8: 结果输出】完成，总计生成 {valid_files} 个有效文件")
    

def load_no_404_from_temp(
                        temp_file_path="temp.txt",
                        category_filter="全选",  # 可选：央视/卫视/港澳台/欧美/其它/全选（可扩展其他分类）
                        quality_filter="全选"    # 可选：4D/超高清/高清/HD/SD/全选
                        ):
    """
    从temp.txt读取数据还原为no_404_items，支持正则匹配分类、画质筛选，新增URL过滤（排除含mp4/audio的URL）
    :param temp_file_path: 读取路径，默认当前目录temp.txt
    :param category_filter: 分类筛选，可选值："央视"、"卫视"、"港澳台"、"欧美"、"其它"、"全选"（不区分大小写）
    :param quality_filter: 画质筛选，可选值："4D/超高清"、"高清/HD"、"SD"、"全选"（不区分大小写）
    :return: 筛选后的StreamItem列表（no_404_items）
    """
    # ========== 1. 定义正则匹配规则 ==========
    # 分类正则配置（排除非中英字符、排除geo-block/persian/firefox等敏感词）
    CATEGORY_PATTERNS = {
        # 央视：匹配关键词 + 忽略大小写
        '央视': re.compile(r'cctv|央视|中国中央电视台', re.I),
        # 卫视：匹配关键词 + 忽略大小写
        '卫视': re.compile(r'卫视', re.I),
        # 港澳台：匹配关键词 + 忽略大小写
        '港澳台': re.compile(r'凤凰|无线|明珠|环球|美亚|翡翠|台视|中视|华视|中天|亚洲', re.I),
        # 欧美：排除unknown + 匹配关键词 + 排除非中英字符 + 排除指定敏感词
        '欧美': re.compile(r'^(?!.*(unknown|geo-block|persian|firefox))[\u4e00-\u9fff0-9a-zA-Z\s\(\)\-_\.!]+(al|ABC|BBC|Bloom|CBS|City|FOX|GB|go2|NBC|News|NTD|UN|Yah|trt|Hollywood)[\u4e00-\u9fffa-zA-Z0-9\s\(\)\-_\.!]+$', re.I),
        # 其它：匹配关键词 + 忽略大小写
        '其它': re.compile(r'(?!.*(unknown|geo-block|persian|firefox))[\u4e00-\u9fff0-9a-zA-Z\s\(\)\-_\.!]+(4K|电影|四川|成都|上海|江苏|南京|新闻|高清|1080p)[\u4e00-\u9fffa-zA-Z0-9\s\(\)\-_\.!]+$', re.I)
    }
    
    # 画质正则配置
    QUALITY_PATTERNS = {
        '4D/超高清': re.compile(r'4k|4d|超高清|uhd', re.I),
        '高清/HD': re.compile(r'高清|hd|1080p', re.I),
        'SD': re.compile(r'sd|标清|720p|480p', re.I)
    }

    # URL过滤正则（匹配含mp4或audio的URL，忽略大小写）
    URL_FILTER_PATTERN = re.compile(r'mp4|audio', re.I)

    # ========== 2. 标准化筛选参数 ==========
    category_filter = category_filter.strip().upper()
    quality_filter = quality_filter.strip().upper()
    
    # 映射用户输入到标准分类名（兼容大小写/简写）
    category_mapping = {
        "央视": ["央视", "CCTV", "中央"],
        "卫视": ["卫视", "WEISHI"],
        "港澳台": ["港澳台", "HKMT", "台湾", "香港", "澳门"],
        "欧美": ["欧美", "EUROPE", "AMERICA", "EN"],
        "其它": ["其它", "OTHER", "其他"],
        "全选": ["全选", "ALL", "QUANXUAN"]
    }
    
    # 映射用户输入到标准画质名
    quality_mapping = {
        "4D/超高清": ["4D/超高清", "4K", "UHD", "超高清"],
        "高清/HD": ["高清/HD", "HD", "高清", "1080P"],
        "SD": ["SD", "标清"],
        "全选": ["全选", "ALL"]
    }

    # ========== 3. 解析用户筛选条件 ==========
    # 匹配分类筛选条件
    selected_category = "全选"
    for std_cat, aliases in category_mapping.items():
        if category_filter in [alias.upper() for alias in aliases]:
            selected_category = std_cat
            break
    
    # 匹配画质筛选条件
    selected_quality = "全选"
    for std_qual, aliases in quality_mapping.items():
        if quality_filter in [alias.upper() for alias in aliases]:
            selected_quality = std_qual
            break
    
    # 提示用户实际生效的筛选条件
    print("筛选条件：分类=%s | 画质=%s | 排除URL含[mp4/audio]" % (selected_category, selected_quality))
    
    # ========== 4. 读取并解析文件 ==========
    no_404_items = []
    total_lines = 0
    filtered_lines = 0
    url_filtered_count = 0  # 新增：统计被URL过滤的条目数
    
    try:
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines):
                line = line.strip()
                total_lines += 1
                
                # 跳过注释行和空行
                if not line or line.startswith("#"):
                    continue
                
                # 按^分割（格式：名称^URL^分类^画质）
                parts = line.split("^")
                if len(parts) != 4:
                    print(f"⚠️  跳过无效行（{line_num+1}行）：{line}")
                    continue
                
                # 解析各字段并解码URL编码的名称
                name = unquote(parts[0].strip())  # 解码URL编码
                url = parts[1].strip()
                raw_category = parts[2].strip() if parts[2].strip() != "无分类" else ""
                raw_quality = parts[3].strip()

                # ========== 新增：URL过滤逻辑（第一步筛选） ==========
                if URL_FILTER_PATTERN.search(url):
                    url_filtered_count += 1
                    print(f"🔕 跳过URL含mp4/audio的条目（{line_num+1}行）：{name} | {url[:50]}...")
                    continue

                # ========== 核心筛选逻辑 ==========
                # 步骤1：正则匹配分类（优先使用文件中的分类，无则自动识别）
                item_category = raw_category if raw_category else None
                if not item_category:
                    # 自动识别分类
                    for cat_name, pattern in CATEGORY_PATTERNS.items():
                        if pattern.search(name):
                            item_category = cat_name
                            break
                    # 未匹配到则归为"其它"
                    item_category = item_category or "其它"
                
                # 步骤2：分类筛选
                if selected_category != "全选" and item_category != selected_category:
                    continue
                
                # 步骤3：正则匹配画质（优先使用文件中的画质，无则自动识别）
                item_quality = raw_quality if raw_quality else None
                if not item_quality:
                    # 自动识别画质
                    for qual_name, pattern in QUALITY_PATTERNS.items():
                        if pattern.search(name):
                            item_quality = qual_name
                            break
                    # 未匹配到则归为"SD"
                    item_quality = item_quality or "SD"
                
                # 步骤4：画质筛选
                if selected_quality != "全选":
                    # 兼容画质名称的不同写法
                    if item_quality not in [selected_quality, 
                                           "高清/HD" if selected_quality == "高清" else "",
                                           "4D/超高清" if selected_quality == "4K" else ""]:
                        continue

                # ========== 筛选通过，创建对象 ==========
                filtered_lines += 1
                item = StreamItem(name, url)
                item.category = item_category
                item.quality = item_quality
                item.passed_404 = True  # 标记为通过404
                item.speed = -1         # 测速值初始化为-1
                item.speed_level = None
                
                no_404_items.append(item)
        
        # 输出筛选统计（新增URL过滤统计）
        print("\n读取完成：")
        print(f"   总计行数：{total_lines}")
        print(f"   有效行数：{len([l for l in lines if l.strip() and not l.startswith('#')])}")
        print(f"   URL过滤：{url_filtered_count} 条（含mp4/audio）")
        print(f"   筛选后：{filtered_lines} 条（符合分类+画质条件）")
        print("   最终返回 %d 条符合所有条件的条目" % len(no_404_items))
        return no_404_items
    
    except FileNotFoundError:
        print(f"❌ 读取失败：文件 {temp_file_path} 不存在")
        return []
    except Exception as e:
        print(f"❌ 读取失败：{e}")
        import traceback
        traceback.print_exc()
        return []
    
# 参照def save_speed_to_temp   speed_test_items 替换 no_404_items
def load_speed_from_temp(
                        temp_file_path="temp_speed.txt",
                        category_filter="全选",  # 可选：央视/卫视/港澳台/欧美/其它/全选（可扩展其他分类）
                        quality_filter="全选",    # 可选：4D/超高清/高清/HD/SD/全选
                        # speedlevel_filter ="wonderful"  可选：excellent，1080p/wonderful,700p/good,500p/useful,200p 
                        ):
    """
    从temp_speed.txt读取数据还原为speed_test_items，支持正则匹配分类、画质筛选，新增URL过滤（排除含mp4/audio的URL）
    :param temp_file_path: 读取路径，默认当前目录temp.txt
    :param category_filter: 分类筛选，可选值："央视"、"卫视"、"港澳台"、"欧美"、"其它"、"全选"（不区分大小写）
    :param quality_filter: 画质筛选，可选值："4D/超高清"、"高清/HD"、"SD"、"全选"（不区分大小写）
    :return: 筛选后的StreamItem列表（speed_test_items）
    """
    # ========== 1. 定义正则匹配规则 ==========
    # 分类正则配置（排除非中英字符、排除geo-block/persian/firefox等敏感词）
    CATEGORY_PATTERNS = {
        # 央视：匹配关键词 + 忽略大小写
        '央视': re.compile(r'cctv|央视|中国中央电视台', re.I),
        # 卫视：匹配关键词 + 忽略大小写
        '卫视': re.compile(r'卫视', re.I),
        # 港澳台：匹配关键词 + 忽略大小写
        '港澳台': re.compile(r'凤凰|无线|明珠|环球|美亚|翡翠|台视|中视|华视|中天|亚洲', re.I),
        # 欧美：排除unknown + 匹配关键词 + 排除非中英字符 + 排除指定敏感词
        '欧美': re.compile(r'^(?!.*(unknown|geo-block|persian|firefox))[\u4e00-\u9fff0-9a-zA-Z\s\(\)\-_\.!]+(al|ABC|BBC|Bloom|CBS|City|FOX|GB|go2|NBC|News|NTD|UN|Yah|trt|Hollywood)[\u4e00-\u9fffa-zA-Z0-9\s\(\)\-_\.!]+$', re.I),
        # 其它：匹配关键词 + 忽略大小写
        '其它': re.compile(r'(?!.*(unknown|geo-block|persian|firefox))[\u4e00-\u9fff0-9a-zA-Z\s\(\)\-_\.!]+(4K|电影|四川|成都|上海|江苏|南京|新闻|高清|1080p)[\u4e00-\u9fffa-zA-Z0-9\s\(\)\-_\.!]+$', re.I)
    }
    
    # 画质正则配置
    QUALITY_PATTERNS = {
        '4D/超高清': re.compile(r'4k|4d|超高清|uhd', re.I),
        '高清/HD': re.compile(r'高清|hd|1080p', re.I),
        'SD': re.compile(r'sd|标清|720p|480p', re.I)
    }

    # URL过滤正则（匹配含mp4或audio的URL，忽略大小写）
    #URL_FILTER_PATTERN = re.compile(r'mp4|audio', re.I)

    # ========== 2. 标准化筛选参数 ==========
    category_filter = category_filter.strip().upper()
    quality_filter = quality_filter.strip().upper()
    
    # 映射用户输入到标准分类名（兼容大小写/简写）
    category_mapping = {
        "央视": ["央视", "CCTV", "中央"],
        "卫视": ["卫视", "WEISHI"],
        "港澳台": ["港澳台", "HKMT", "台湾", "香港", "澳门"],
        "欧美": ["欧美", "EUROPE", "AMERICA", "EN"],
        "其它": ["其它", "OTHER", "其他"],
        "全选": ["全选", "ALL", "QUANXUAN"]
    }
    
    # 映射用户输入到标准画质名
    quality_mapping = {
        "4D/超高清": ["4D/超高清", "4K", "UHD", "超高清"],
        "高清/HD": ["高清/HD", "HD", "高清", "1080P"],
        "SD": ["SD", "标清"],
        "全选": ["全选", "ALL"]
    }

    # ========== 3. 解析用户筛选条件 ==========
    # 匹配分类筛选条件
    selected_category = "全选"
    for std_cat, aliases in category_mapping.items():
        if category_filter in [alias.upper() for alias in aliases]:
            selected_category = std_cat
            break
    
    # 匹配画质筛选条件
    selected_quality = "全选"
    for std_qual, aliases in quality_mapping.items():
        if quality_filter in [alias.upper() for alias in aliases]:
            selected_quality = std_qual
            break
    
    # 提示用户实际生效的筛选条件
    print("筛选条件：分类=%s | 画质=%s | 排除URL含[mp4/audio]" % (selected_category, selected_quality))
    
    # ========== 4. 读取并解析文件 ==========
    speed_test_items = []
    total_lines = 0
    filtered_lines = 0
    url_filtered_count = 0  # 新增：统计被URL过滤的条目数
    
    try:
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines):
                line = line.strip()
                total_lines += 1
                
                # 跳过注释行和空行
                if not line or line.startswith("#"):
                    continue
                
                # 按^分割（格式：名称^URL^分类^画质）
                parts = line.split("^")
                if len(parts) != 6:
                    print(f"⚠️  跳过无效行（{line_num+1}行）：{line}")
                    continue
                
                # 解析各字段并解码URL编码的名称
                name = unquote(parts[0].strip())  # 解码URL编码
                url = parts[1].strip()
                raw_category = parts[2].strip() if parts[2].strip() != "无分类" else ""
                raw_quality = parts[3].strip()
                raw_speed = parts[4].strip()
                raw_speedlever = parts[5].strip()
                '''
                # ========== 新增：URL过滤逻辑（第一步筛选） ==========
                if URL_FILTER_PATTERN.search(url):
                    url_filtered_count += 1
                    print(f"🔕 跳过URL含mp4/audio的条目（{line_num+1}行）：{name} | {url[:50]}...")
                    continue
                '''
                # ========== 核心筛选逻辑 ==========
                # 步骤1：正则匹配分类（优先使用文件中的分类，无则自动识别）
                item_category = raw_category if raw_category else None
                if not item_category:
                    # 自动识别分类
                    for cat_name, pattern in CATEGORY_PATTERNS.items():
                        if pattern.search(name):
                            item_category = cat_name
                            break
                    # 未匹配到则归为"其它"
                    item_category = item_category or "其它"
                
                # 步骤2：分类筛选
                if selected_category != "全选" and item_category != selected_category:
                    continue
                
                # 步骤3：正则匹配画质（优先使用文件中的画质，无则自动识别）
                item_quality = raw_quality if raw_quality else None
                if not item_quality:
                    # 自动识别画质
                    for qual_name, pattern in QUALITY_PATTERNS.items():
                        if pattern.search(name):
                            item_quality = qual_name
                            break
                    # 未匹配到则归为"SD"
                    item_quality = item_quality or "SD"
                
                # 步骤4：画质筛选
                if selected_quality != "全选":
                    # 兼容画质名称的不同写法
                    if item_quality not in [selected_quality, 
                                           "高清/HD" if selected_quality == "高清" else "",
                                           "4D/超高清" if selected_quality == "4K" else ""]:
                        continue

                # ========== 筛选通过，创建对象 ==========
                filtered_lines += 1
                item = StreamItem(name, url)
                item.category = item_category
                item.quality = item_quality
                item.passed_404 = True  # 标记为通过404
                
                # 确保speed是整数类型
                try:
                    item.speed = int(float(raw_speed)) if raw_speed and raw_speed != "-1" else -1
                except (ValueError, TypeError):
                    item.speed = -1
                    
                item.speed_level = raw_speedlever
                
                speed_test_items.append(item)
        
        # 输出筛选统计（新增URL过滤统计）
        print("\n读取完成：")
        print(f"   总计行数：{total_lines}")
        print(f"   有效行数：{len([l for l in lines if l.strip() and not l.startswith('#')])}")
        print(f"   URL过滤：{url_filtered_count} 条（含mp4/audio）")
        print(f"   筛选后：{filtered_lines} 条（符合分类+画质条件）")
        print("   最终返回 %d 条符合所有条件的条目" % len(speed_test_items))
        return speed_test_items
    
    except FileNotFoundError:
        print(f"❌ 读取失败：文件 {temp_file_path} 不存在")
        return []
    except Exception as e:
        print(f"❌ 读取失败：{e}")
        import traceback
        traceback.print_exc()
        return []
    

    

def save_no_404_to_temp(no_404_items, temp_file_path="temp.txt"):
    """
    命令1：将no_404_items保存为temp.txt中间文件
    :param no_404_items: 通过404检测的StreamItem列表
    :param temp_file_path: 保存路径，默认当前目录temp.txt
    """
    try:
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            # 写入文件头（标识格式）
            f.write("# LIVE_STREAM_TEMP_FILE\n\n")
            f.write("# 格式：名称^URL^分类^画质\n\n")
            # 遍历写入每个条目（用|分隔避免URL中的,干扰）
            for item in no_404_items:
                # 处理空值，避免写入None
                category = item.category if item.category else "无分类"
                quality = item.quality if item.quality else "SD"
                # 写入行：名称|URL|分类|画质
                line = f"{item.name}^{item.url}^{category}^{quality}\n"
                f.write(line)
        print("命令1执行完成：no_404_items已保存至 %s" % temp_file_path)
        print("共保存 %d 条条目" % len(no_404_items))
    except Exception as e:
        print(f"❌ 命令1执行失败：{e}")

def save_speed_to_temp(speed_test_items, temp_file_path="temp_speed.txt"):
    """
    命令1：将speed_test_items保存为temp_speed.txt中间文件
    :param speed_test_items: 速度测试后的StreamItem列表
    :param temp_file_path: 保存路径，默认当前目录temp_speed.txt
    :param no_404_items: 通过404检测的StreamItem列表
    :param temp_file_path: 保存路径，默认当前目录temp.txt
    """
    try:
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            # 写入文件头（标识格式）
            f.write("# LIVE_STREAM_TEMP_FILE\n\n")
            f.write("# 格式：名称^URL^分类^画质^速度^速度评级\n\n")
            # 遍历写入每个条目（用|分隔避免URL中的,干扰）
            for item in speed_test_items:
                # 处理空值，避免写入None
                category = item.category if item.category else "无分类"
                quality = item.quality if item.quality else "SD"
                speed = item.speed if item.speed else "-1"
                speed_level = item.speed_level if item.speed_level else "useful"
                # 写入行：名称|URL|分类|画质
                line = f"{item.name}^{item.url}^{category}^{quality}^{speed}^{speed_level}\n"
                f.write(line)
        print("命令1执行完成：speed_test_items已保存至 %s" % temp_file_path)
        print("共保存 %d 条条目" % len(speed_test_items))
    except Exception as e:
        print(f"❌ 命令1执行失败：{e}")



# ======================== 主执行流程 ========================
def main():
    """主函数"""
    init_data = init()
    
    try:
        raw_items = load_resources()
        gc.collect()  # 强制垃圾回收
        
        #raw_items = []

        
        dedup_items = deduplicate_items(raw_items)
        gc.collect()  # 强制垃圾回收
        
        filtered_items = filter_items(dedup_items)
        gc.collect()  # 强制垃圾回收
        
        no_404_items = check_404(filtered_items)
        gc.collect()  # 强制垃圾回收
        
        # ========== 命令1：保存到temp.txt ==========
        #save_no_404_to_temp(no_404_items, "temp.txt")  # 保存到当前目录
        
        # ========== 命令2：从temp.txt读取还原（调试/复用场景） ==========
        # 场景1：直接复用（比如跳过404筛查，直接用之前的结果）
        # no_404_items = load_no_404_from_temp(
        #                            temp_file_path="temp.txt",
        #                            category_filter="全选",  # 可选：央视/欧美/全选（可扩展其他分类）
        #                            quality_filter="全选"    # 可选：4D/超高清/高清/全选
        #                            )
        
        # 继续后续流程
        
        
        
        speed_test_items = test_speed(no_404_items)
        gc.collect()  # 强制垃圾回收
        
        # 过滤出有效测速的条目（speed > 0）
        valid_speed_items = [item for item in speed_test_items if item.speed > 204800]
        print(f"\n【过滤有效测速条目】总计测速 {len(speed_test_items)} 条 → 有效测速 {len(valid_speed_items)} 条")
        
        #valid_speed_items =load_speed_from_temp(
        #                        temp_file_path="temp_speed.txt",
        #                        category_filter="全选",  # 可选：央视/卫视/港澳台/欧美/其它/全选（可扩展其他分类）
        #                        quality_filter="全选",    # 可选：4D/超高清/高清/HD/SD/全选
                                # speedlevel_filter ="wonderful"  可选：excellent，1080p/wonderful,700p/good,500p/useful,200p 
        #                        )
        
        
        
        # ========== 新增：画面有效性检测 ==========
        # 基于IPTV API模式的异步内存管理
        print(f"\n【画面检测】基于IPTV API模式处理 {len(valid_speed_items)} 个条目")
        
        # 尝试导入异步内存管理器
        try:
            import asyncio
            from async_memory_manager import AsyncMemoryManager
            
            async def async_video_detection():
                """异步画面检测"""
                manager = AsyncMemoryManager(max_concurrent=5, memory_threshold=75.0)
                
                def check_video_wrapper(item):
                    """画面检测包装器"""
                    try:
                        # 单线程检测避免内存问题
                        result = check_video_validity([item], max_threads=1)
                        return result[0] if result else None
                    except Exception as e:
                        print(f"[异步检测] 处理失败: {e}")
                        return None
                
                try:
                    # 异步批量处理
                    video_valid_items = await manager.process_with_memory_control(
                        valid_speed_items,
                        check_video_wrapper,
                        max_memory_mb=1200  # 限制内存使用
                    )
                    
                    # 过滤有效结果
                    video_valid_items = [item for item in video_valid_items if item is not None]
                    
                    # 打印统计
                    stats = manager.get_stats()
                    print(f"[异步统计] 处理{stats['total_processed']}个, "
                          f"有效{len(video_valid_items)}个, "
                          f"内存警告{stats['memory_warnings']}次")
                    
                    return video_valid_items
                    
                finally:
                    manager.cleanup()
            
            # 运行异步检测
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            video_valid_items = loop.run_until_complete(async_video_detection())
            loop.close()
            
        except ImportError as e:
            print(f"[异步检测] 异步管理器不可用: {e}")
            print(f"[画面检测] 使用同步模式处理 {len(valid_speed_items)} 个条目")
            
            # 同步模式 - 基于IPTV API的批量处理
            import copy
            
            # 深拷贝避免内存污染
            items_copy = copy.deepcopy(valid_speed_items)
            
            # 分批处理
            batch_size = 30  # 较小批次
            video_valid_items = []
            
            for i in range(0, len(items_copy), batch_size):
                batch = items_copy[i:i+batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(items_copy) - 1) // batch_size + 1
                
                print(f"\n【画面检测批次】{batch_num}/{total_batches} | 本批数量: {len(batch)}")
                
                # 内存检查
                try:
                    import psutil
                    memory_percent = psutil.virtual_memory().percent
                    print(f"[内存监控] 批次开始前内存: {memory_percent:.1f}%")
                    
                    if memory_percent > 75:
                        print("[内存警告] 批次前内存过高，强制垃圾回收")
                        gc.collect()
                        time.sleep(2)
                except ImportError:
                    pass
                
                # 处理批次
                try:
                    batch_results = check_video_validity(batch, max_threads=1)
                    video_valid_items.extend(batch_results)
                except Exception as e:
                    print(f"[批次错误] 处理失败: {e}")
                
                # 强制垃圾回收
                gc.collect()
                
                # 批次后内存检查
                try:
                    import psutil
                    memory_percent = psutil.virtual_memory().percent
                    print(f"[内存监控] 批次完成后内存: {memory_percent:.1f}%")
                    
                    if memory_percent > 80:
                        print("[内存警告] 内存使用过高，暂停5秒")
                        time.sleep(5)
                        gc.collect()
                except ImportError:
                    pass
                
                # 清理批次数据
                del batch
                gc.collect()
            
            # 清理拷贝数据
            del items_copy
            gc.collect()
        
        # 最终垃圾回收
        gc.collect()

        # 结果整理（仅保留视频有效条目）
        
        organized_data = organize_results(video_valid_items)
        export_results(organized_data, init_data['daytime'])
        
        total_time = time.perf_counter() - init_data['start_time']
        print("\n" + "="*80)
        print(f"【全部步骤完成】总耗时：{total_time:.2f} 秒（{total_time/60:.1f} 分钟）")
        print(f"完成时间：{get_beijing_time('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
    except Exception as e:
        print(f"\n【程序执行出错】{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 最终强制垃圾回收
        gc.collect()
        
if __name__ == "__main__":
    if sys.platform == 'win32':
        multiprocessing.freeze_support()
    main()