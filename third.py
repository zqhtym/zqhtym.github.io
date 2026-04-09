#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV检测工具 - Step7及以后步骤
从step6_video_resources.csv开始运行，完成Step7和Step8
"""

import asyncio
import os
import time
import os
from datetime import datetime
from typing import List

# 导入独立模块
from iptv_checker import IPTVChecker

class ThirdChecker(IPTVChecker):
    """Step7及以后的步骤检查器"""
    
    def __init__(self):
        super().__init__()
    
    async def _run_conversion_tools(self):
        """运行转换工具 - 第三步专用，将exe复制到output目录"""
        import subprocess
        import shutil
        from pathlib import Path
        
        # 获取最新的文件
        output_dir = Path("output")
        utils_dir = Path("utils")
        
        #  Python 
        py_source = Path("debug_file.py")  # Python 
        py_target = output_dir / "debug_file.py"
        
        #  Python 
        if py_source.exists():
            try:
                shutil.copy2(py_source, py_target)
                print(f" Python : {py_target}")
            except Exception as e:
                print(f" Python : {e}")
                return
        else:
            print(f" Python ")
            return
        
        # 只处理LE.txt和LU.txt文件
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
        if le_file.exists():
            print(f" LE.txt -> LE.m3u")
            try:
                #  Python 
                py_path = py_target
                if py_path.exists():
                    try:
                        subprocess.run(["python", str(py_path), "LE.txt", "LE.m3u"], 
                                     cwd=output_dir, check=True, capture_output=True, text=True)
                        print(f" LE.m3u (Python)")
                        # 
                        debug_file = output_dir / "../tmp/debug.log"
                        if debug_file.exists():
                            print(" :")
                            with open(debug_file, 'r') as f:
                                print(f.read())
                    except (subprocess.CalledProcessError, FileNotFoundError) as e:
                        print(f" Python: {str(e)}")
                        # 
                        debug_file = output_dir / "../tmp/debug.log"
                        if debug_file.exists():
                            print(" :")
                            with open(debug_file, 'r') as f:
                                print(f.read())
                else:
                    print(f" Python ")
                    
            except Exception as e:
                print(f" : {e}")
        
        if lu_file.exists():
            print(f" LU.txt -> LU.m3u")
            try:
                #  Python 
                py_path = py_target
                if py_path.exists():
                    try:
                        subprocess.run(["python", str(py_path), "LU.txt", "LU.m3u"], 
                                     cwd=output_dir, check=True, capture_output=True, text=True)
                        print(f" LU.m3u (Python)")
                        # 
                        debug_file = output_dir / "../tmp/debug.log"
                        if debug_file.exists():
                            print(" :")
                            with open(debug_file, 'r') as f:
                                print(f.read())
                    except (subprocess.CalledProcessError, FileNotFoundError) as e:
                        print(f" Python: {str(e)}")
                        # 
                        debug_file = output_dir / "../tmp/debug.log"
                        if debug_file.exists():
                            print(" :")
                            with open(debug_file, 'r') as f:
                                print(f.read())
                else:
                    print(f" Python ")
                    
            except Exception as e:
                print(f" : {e}")
    
    async def _generate_results(self, video_resources: List[dict]):
        """生成最终结果文件 - third.py专用，只输出LE.txt和LU.txt"""
        from pathlib import Path
        from datetime import datetime
        
        # 创建输出目录
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 按速度分类
        excellent_resources = []  # >= 2MB/s
        wonderful_resources = []  # >= 1MB/s  
        good_resources = []      # >= 0.7MB/s
        useful_resources = []     # >= 0.5MB/s
        
        for resource in video_resources:
            speed = resource.get('speed', 0)
            if speed >= 2.0:
                excellent_resources.append(resource)
            elif speed >= 1.0:
                wonderful_resources.append(resource)
            elif speed >= 0.7:
                good_resources.append(resource)
            elif speed >= 0.5:
                useful_resources.append(resource)
        
        # 生成 LE.txt 和 LU.txt (兼容原有格式)
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
        # LE.txt: 包含所有级别的资源
        all_resources = useful_resources + good_resources + wonderful_resources + excellent_resources
        with open(le_file, 'w', encoding='utf-8') as f:
            for resource in all_resources:
                f.write(f"{resource['name']},{resource['url']}\n")
        
        # LU.txt: 只包含 good 及以上级别的资源
        lu_resources = good_resources + wonderful_resources + excellent_resources
        with open(lu_file, 'w', encoding='utf-8') as f:
            for resource in lu_resources:
                f.write(f"{resource['name']},{resource['url']}\n")
        
        # 统计信息
        total_channels = len(set(r['name'] for r in video_resources))
        good_channels = len(set(r['name'] for r in lu_resources))
        
        print(f"✅ 生成 LE.txt: {len(all_resources)} 个资源")
        print(f"✅ 生成 LU.txt: {len(lu_resources)} 个资源")
        print(f"   good: 总频道={total_channels}, 符合条件={good_channels}")
        print(f"📊 文件生成完成: LE.txt + LU.txt (third.py专用模式)")
    
    async def _cleanup_output_directory(self):
        """清理output目录，删除不需要的文件，保留CSV中间文件和最终文件"""
        import glob
        from pathlib import Path
        
        output_dir = Path("output")
        
        # 需要保留的文件模式
        keep_patterns = [
            "step*.csv",           # 中间CSV文件
            "LE.txt", "LU.txt",    # 最终txt文件
            "LE.m3u", "LU.m3u",    # 最终m3u文件
            "txt_to_m3u8b.py",     # Python
            "ffmpeg.exe"             # FFmpeg
        ]
        
        # 需要删除的文件模式
        delete_patterns = [
            "live+*.txt",           # 分级txt文件（删除）
            "*.txt.bak", "*.csv.bak" # 备份文件（删除）
        ]
        
        # 注意：不删除live+*.csv，因为包含分级结果
        # 注意：不删除step*.csv，因为包含中间结果
        
        # 特别保护：确保txt_to_m3u8b.py不被删除
        py_file = output_dir / "txt_to_m3u8b.py"
        if py_file.exists():
            print(f" : txt_to_m3u8b.py")
        
        print(" 检查需要清理的文件...")
        
        deleted_count = 0
        for pattern in delete_patterns:
            files = glob.glob(str(output_dir / pattern))
            for file in files:
                try:
                    os.remove(file)
                    print(f"🗑️ 删除: {Path(file).name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️ 删除失败 {Path(file).name}: {e}")
        
        print(f"✅ 清理完成，删除了 {deleted_count} 个文件")
    
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
            
            # 清理output目录，只保留CSV中间文件
            print(f"\n🧹 清理output目录")
            print("-" * 50)
            await self._cleanup_output_directory()
            
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
