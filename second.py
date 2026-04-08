#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV检测工具 - Step6及以后步骤
从step5_speed_resources.csv开始运行Step6、Step7、Step8
Author: chaichunyang@outlook.com
"""

import asyncio
import copy
import os
import sys
import time as time_module
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union, Optional
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
from functools import partial
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import multiprocessing

from tqdm import tqdm

# 导入独立模块
from iptv_checker import IPTVChecker

class SecondChecker(IPTVChecker):
    """Step6及以后的步骤检查器"""
    
    def __init__(self):
        super().__init__()
    
    async def run_from_step6(self):
        """从Step6开始运行"""
        try:
            main_start_time = time_module.time()
            
            print("=" * 80)
            print(f"【IPTV检测工具 - Step6及以后】开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"从step5_speed_resources.csv开始运行")
            print("=" * 80)
            
            # 读取Step5结果文件
            step5_csv_path = "output/step5_speed_resources.csv"
            if not os.path.exists(step5_csv_path):
                print(f"❌ Step5结果文件不存在：{step5_csv_path}")
                print(f"请先运行main.py完成Step1~Step5的工作")
                return
            
            print(f"\n📊 从Step6开始：读取Step5结果文件")
            print("-" * 50)
            
            speed_resources = self._read_step5_csv_resources(step5_csv_path)
            
            if not speed_resources:
                print(f"❌ Step5 CSV文件读取失败或为空")
                return
            
            print(f"📊 Step5资源读取完成: {len(speed_resources)} 个资源")
            
            # 显示Step5资源统计
            self._print_step_resources("Step5(从文件)", speed_resources, speed_resources, 
                                    "从CSV文件加载")
            
            # Step6: 画面变化与有声音项目筛查
            print(f"\n📊 Step6: 画面变化与有声音项目筛查")
            print("-" * 50)
            
            video_resources = await self._check_video_with_progress(speed_resources)
            
            print(f"\n📊 Step6完成:")
            if len(speed_resources) > 0:
                success_rate = (len(video_resources)/len(speed_resources)*100) if len(speed_resources) > 0 else 0
                self._print_step_resources("Step6", speed_resources, video_resources, 
                                        f"画面检测成功率: {success_rate:.1f}%")
                
                # 输出Step6接口文件
                self._save_step_output("step6_video_resources.csv", video_resources, "Step6: 画面变化与声音筛查后资源")
            else:
                print(f"   输入资源: 0")
                print(f"   输出资源: 0")
                print(f"   检测成功率: 0.0%")
                video_resources = []  # 确保video_resources存在
            
            # Step6完成 - 生成step6_video_resources.csv文件
            print(f"\n🎉 Step6完成！")
            print(f"� 已生成step6_video_resources.csv文件，包含{len(video_resources)}个资源")
            print(f"� 请运行third.py继续Step7及以后的步骤")
            return  # Step6完成，结束运行
            
        except Exception as e:
            print(f"❌ Step6及以后步骤失败: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """主函数"""
    checker = SecondChecker()
    await checker.run_from_step6()

if __name__ == "__main__":
    asyncio.run(main())
