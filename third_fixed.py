#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV - Step7
Step6_video_resources.csv
"""

import asyncio
import os
import time
from datetime import datetime
from typing import List

#  IPTVChecker
from iptv_checker import IPTVChecker

class ThirdChecker(IPTVChecker):
    """Step7"""
    
    def __init__(self):
        super().__init__()
    
    async def _run_conversion_tools(self):
        """ -  exe"""
        import subprocess
        import shutil
        from pathlib import Path
        
        # 
        output_dir = Path("output")
        
        #  txt_to_m3u8b.exe
        exe_source = Path("../txt_to_m3u8b.exe")  #  exe
        exe_target = output_dir / "txt_to_m3u8b.exe"
        
        if exe_source.exists():
            try:
                shutil.copy2(exe_source, exe_target)
                print(f" : {exe_target}")
            except Exception as e:
                print(f" exe: {e}")
                return
        elif exe_target.exists():
            print(f" txt_to_m3u8b.exe : {exe_target}")
        else:
            print(f" txt_to_m3u8b.exe")
        
        #  LE.txt LU.txt
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
        if le_file.exists():
            print(f" LE.txt -> LE.m3u")
            try:
                #  output exe
                exe_path = exe_target
                bat_path = output_dir / "txt_to_m3u8b.bat"
                py_path = output_dir / "txt_to_m3u8b.py"
                
                #  exe
                if exe_path.exists():
                    try:
                        result = subprocess.run([str(exe_path), "LE.txt", "LE.m3u"], 
                                             cwd=output_dir, check=True, capture_output=True, text=True)
                        print(f" LE.m3u (Exe)")
                    except (subprocess.CalledProcessError, PermissionError, FileNotFoundError) as e:
                        print(f" exe: {str(e)} Python")
                        # exe Python
                        if py_path.exists():
                            try:
                                subprocess.run(["python", str(py_path), "LE.txt", "LE.m3u"], 
                                             cwd=output_dir, check=True, capture_output=True, text=True)
                                print(f" LE.m3u (Python)")
                            except (subprocess.CalledProcessError, FileNotFoundError):
                                # Python bat
                                if bat_path.exists():
                                    subprocess.run([str(bat_path), "LE.txt", "LE.m3u"], 
                                                 cwd=output_dir, check=True)
                                    print(f" LE.m3u (Bat)")
                                else:
                                    print(f" ")
                        else:
                            print(f" Python")
                else:
                    print(f" exe: txt_to_m3u8b.exe")
                    
            except Exception as e:
                print(f" : {e}")
        
        if lu_file.exists():
            print(f" LU.txt -> LU.m3u")
            try:
                #  output exe
                exe_path = exe_target
                bat_path = output_dir / "txt_to_m3u8b.bat"
                py_path = output_dir / "txt_to_m3u8b.py"
                
                #  exe
                if exe_path.exists():
                    try:
                        result = subprocess.run([str(exe_path), "LU.txt", "LU.m3u"], 
                                             cwd=output_dir, check=True, capture_output=True, text=True)
                        print(f" LU.m3u (Exe)")
                    except (subprocess.CalledProcessError, PermissionError, FileNotFoundError) as e:
                        print(f" exe: {str(e)} Python")
                        # exe Python
                        if py_path.exists():
                            try:
                                subprocess.run(["python", str(py_path), "LU.txt", "LU.m3u"], 
                                             cwd=output_dir, check=True, capture_output=True, text=True)
                                print(f" LU.m3u (Python)")
                            except (subprocess.CalledProcessError, FileNotFoundError):
                                # Python bat
                                if bat_path.exists():
                                    subprocess.run([str(bat_path), "LU.txt", "LU.m3u"], 
                                                 cwd=output_dir, check=True)
                                    print(f" LU.m3u (Bat)")
                                else:
                                    print(f" ")
                        else:
                            print(f" Python")
                else:
                    print(f" exe: txt_to_m3u8b.exe")
                    
            except Exception as e:
                print(f" : {e}")
    
    async def _generate_results(self, video_resources: List[dict]):
        """ - third.py LE.txt LU.txt"""
        from pathlib import Path
        from datetime import datetime
        
        # 
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 
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
        
        #  LE.txt LU.txt ()
        le_file = output_dir / "LE.txt"
        lu_file = output_dir / "LU.txt"
        
        # LE.txt: 
        all_resources = useful_resources + good_resources + wonderful_resources + excellent_resources
        with open(le_file, 'w', encoding='utf-8') as f:
            for resource in all_resources:
                f.write(f"{resource['name']},{resource['url']}\n")
        
        # LU.txt:  good 
        lu_resources = good_resources + wonderful_resources + excellent_resources
        with open(lu_file, 'w', encoding='utf-8') as f:
            for resource in lu_resources:
                f.write(f"{resource['name']},{resource['url']}\n")
        
        # 
        total_channels = len(set(r['name'] for r in video_resources))
        good_channels = len(set(r['name'] for r in lu_resources))
        
        print(f" LE.txt: {len(all_resources)} ")
        print(f" LU.txt: {len(lu_resources)} ")
        print(f"   good: ={total_channels}, ={good_channels}")
        print(f" : LE.txt + LU.txt (third.py)")
    
    async def _cleanup_output_directory(self):
        """ output CSV"""
        import glob
        from pathlib import Path
        
        output_dir = Path("output")
        
        # 
        keep_patterns = [
            "step*.csv",           # CSV
            "LE.txt", "LU.txt",    # txt
            "LE.m3u", "LU.m3u",    # m3u
            "txt_to_m3u8b.exe",     # ()
            "ffmpeg.exe"             # FFmpeg()
        ]
        
        # 
        delete_patterns = [
            "live+*.txt",           # txt()
            "*.txt.bak", "*.csv.bak" # ()
        ]
        
        # : live+*.csv
        # : step*.csv
        
        # : txt_to_m3u8b.exe
        exe_file = output_dir / "txt_to_m3u8b.exe"
        if exe_file.exists():
            print(f" : txt_to_m3u8b.exe")
        
        print(" ...")
        
        deleted_count = 0
        for pattern in delete_patterns:
            files = glob.glob(str(output_dir / pattern))
            for file in files:
                try:
                    os.remove(file)
                    print(f" : {Path(file).name}")
                    deleted_count += 1
                except Exception as e:
                    print(f" {Path(file).name}: {e}")
        
        print(f" : {deleted_count} ")
    
    async def run_from_step7(self):
        """Step7"""
        try:
            main_start_time = time.time()
            
            print("=" * 80)
            print(f" IPTV - Step7 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"step6_video_resources.csv")
            print("=" * 80)
            
            #  Step6
            step6_csv_path = "output/step6_video_resources.csv"
            if not os.path.exists(step6_csv_path):
                print(f" Step6: {step6_csv_path}")
                print(f" second.py Step6")
                return
            
            print(f"\n Step7: Step6")
            print("-" * 50)
            
            video_resources = self._read_step6_csv_resources(step6_csv_path)
            
            if not video_resources:
                print(" Step6")
                return
            
            print(f"  {len(video_resources)} Step6")
            
            #  output CSV
            print(f"\n output")
            print("-" * 50)
            await self._cleanup_output_directory()
            
            # Step7: 
            print(f"\n Step7: ")
            print("-" * 50)
            
            await self._generate_results(video_resources)
            
            # Step8: 
            print(f"\n Step8: ")
            print("-" * 50)
            
            await self._run_conversion_tools()
            
            # 
            main_end_time = time.time()
            print(f"\n !: {self._format_duration(main_end_time - main_start_time)}")
            print(f" Step7: Step6={len(video_resources)}")
            
        except Exception as e:
            print(f" Step7: {e}")
            import traceback
            traceback.print_exc()
    
    def _read_step6_csv_resources(self, file_path: str) -> list:
        """Step6 CSV"""
        resources = []
        lines = []
        
        # 
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                print(f"  {encoding} Step6 CSV")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f" Step6 CSV: {e}")
                return resources
        
        if not lines:
            print(" Step6 CSV")
            return resources
        
        current_category = ""
        current_speed = 0.0
        has_video = False
        has_audio = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 
            if line.startswith('#') and ('Step6' in line or '' in line or '' in line or '' in line or line.startswith('#' * 50)):
                continue
            
            #  , # [ 0.582MB/s
            if line.startswith('# [') and 'MB/s' in line:
                try:
                    # 
                    if ']' in line:
                        category_part = line[line.find('[') + 1:line.find(']')]
                        if category_part:
                            current_category = category_part.strip()
                    
                    # 
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
            
            # , : URL
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
    """ """
    checker = ThirdChecker()
    await checker.run_from_step7()

if __name__ == "__main__":
    asyncio.run(main())
