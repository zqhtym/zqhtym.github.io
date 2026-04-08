#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV检测工具 - Step7及以后步骤
从step6_video_resources.csv开始运行，完成Step7和Step8
"""

import asyncio
import os
import sys
import time
from datetime import datetime

# 导入独立模块
from iptv_checker import IPTVChecker

class ThirdChecker(IPTVChecker):
    """Step7及以后的步骤检查器"""
    
    def __init__(self):
        super().__init__()
    
    async def run_from_step7(self):
        """从Step7开始运行"""
        try:
            main_start_time = time.time()
            
            print("=" * 80)
            print(f"【IPTV检测工具 - Step7及以后】开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"从step6_video_resources.csv开始运行")
            print("=" * 80)
            
            # 读取Step6结果文件
            step6_csv_path = "output/step6_video_resources.csv"
            if not os.path.exists(step6_csv_path):
                print(f"❌ Step6结果文件不存在：{step6_csv_path}")
                print(f"请先运行second.py完成Step6的工作")
                return
            
            print(f"\n📊 从Step7开始：读取Step6结果文件")
            print("-" * 50)
            
            video_resources = self._read_step6_csv_resources(step6_csv_path)
            
            if not video_resources:
                print("❌ 未读取到任何Step6资源")
                return
            
            print(f"✅ 成功读取 {len(video_resources)} 个Step6资源")
            
            # Step7: 结果整理输出
            print(f"\n📊 Step7: 结果整理输出")
            print("-" * 50)
            
            await self._generate_results(video_resources)
            
            # Step8: 运行转换工具
            print(f"\n📊 Step8: 运行转换工具")
            print("-" * 50)
            
            await self._run_conversion_tools()
            
            # 最终统计
            main_end_time = time.time()
            print(f"\n🎉 检测完成！总耗时: {self._format_duration(main_end_time - main_start_time)}")
            print(f"📊 从Step7开始统计: Step6={len(video_resources)}")
            
        except Exception as e:
            print(f"❌ Step7及以后步骤失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _read_step6_csv_resources(self, file_path: str) -> list:
        """读取Step6 CSV文件资源"""
        resources = []
        lines = []
        
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                print(f"📋 使用编码 {encoding} 读取Step6 CSV文件成功")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"❌ 读取Step6 CSV文件失败: {e}")
                return resources
        
        if not lines:
            print("❌ 无法读取Step6 CSV文件")
            return resources
        
        current_category = "默认分类"
        current_speed = 0.0
        has_video = False
        has_audio = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 跳过文件头注释
            if line.startswith('#') and ('Step6' in line or '生成时间' in line or '资源数量' in line or '平均速度' in line or line.startswith('#' * 50)):
                continue
            
            # 解析分类和速度信息行，如：# [其它] 0.582MB/s
            if line.startswith('# [') and 'MB/s' in line:
                try:
                    # 提取分类信息
                    if ']' in line:
                        category_part = line[line.find('[') + 1:line.find(']')]
                        if category_part:
                            current_category = category_part.strip()
                    
                    # 提取速度信息
                    if 'MB/s' in line:
                        speed_part = line[line.find('MB/s') - 10:line.find('MB/s')]
                        speed_str = speed_part.strip().split()[-1]
                        try:
                            current_speed = float(speed_str)
                        except ValueError:
                            current_speed = 0.0
                except Exception:
                    pass
                continue
            
            # 解析资源行，格式：名称,URL
            if ',' in line and not line.startswith('#'):
                try:
                    parts = line.split(',', 1)
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        url = parts[1].strip()
                        
                        if name and url and url.startswith('http'):
                            resource = {
                                'name': name,
                                'url': url,
                                'category': current_category,
                                'speed': current_speed,
                                'has_video': has_video,
                                'has_audio': has_audio,
                                'is_whitelist': False
                            }
                            resources.append(resource)
                except Exception:
                    pass
        
        return resources

async def main():
    """主函数"""
    checker = ThirdChecker()
    await checker.run_from_step7()

if __name__ == "__main__":
    asyncio.run(main())
