#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_ffmpeg.py - 测试FFmpeg检测功能

import os
import sys
import shutil

def test_ffmpeg_detection():
    """测试FFmpeg检测功能"""
    print("=== FFmpeg Detection Test ===")
    
    # 模拟GitHub Actions环境
    print("\n1. System PATH detection:")
    if shutil.which('ffmpeg'):
        print(f"[OK] Found FFmpeg in PATH: {shutil.which('ffmpeg')}")
    else:
        print("[FAIL] FFmpeg not found in PATH")
    
    # 模拟GitHub Actions环境
    print("\n2. GitHub Actions environment detection:")
    original_github = os.environ.get('GITHUB_ACTIONS')
    os.environ['GITHUB_ACTIONS'] = 'true'
    
    # 导入并测试video_check_worker的FFmpeg检测
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from video_check_worker import check_ffmpeg
        
        github_result = check_ffmpeg()
        if github_result:
            print("[OK] FFmpeg detection in GitHub Actions environment successful")
        else:
            print("[FAIL] FFmpeg detection in GitHub Actions environment failed")
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
    finally:
        # 恢复原始环境变量
        if original_github:
            os.environ['GITHUB_ACTIONS'] = original_github
        else:
            os.environ.pop('GITHUB_ACTIONS', None)
    
    # 测试GitHub Actions专用版本
    print("\n3. GitHub Actions dedicated version detection:")
    try:
        from video_check_worker_github import check_ffmpeg as check_ffmpeg_github
        
        github_result = check_ffmpeg_github()
        if github_result:
            print("[OK] GitHub Actions dedicated version FFmpeg detection successful")
        else:
            print("[FAIL] GitHub Actions dedicated version FFmpeg detection failed")
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
    
    # 测试本地Windows环境
    print("\n4. Local Windows environment detection:")
    if sys.platform.startswith('win'):
        print("Windows environment, checking common paths...")
        
        # 检查常见Windows路径
        windows_paths = [
            r'H:\11 tool\装机\视频\哔哩下载姬（downkyi）-27-1.3.4\ffmpeg.exe',
            r'C:\Users\Administrator\AppData\Roaming\anythingllm-desktop\storage\engines\ffmpeg\windows-x64\ffmpeg.exe',
            r'C:\Program Files\iGameCenter\SAVIConverter\tools\ffmpeg.exe',
            r'C:\Users\Administrator\AppData\Local\Programs\icat\resources\bin\ffmpeg\ffmpeg.exe',
            r'C:\ffmpeg\ffmpeg.exe',
            r'C:\ffmpeg\bin\ffmpeg.exe'
        ]
        
        found_paths = []
        for path in windows_paths:
            if os.path.exists(path):
                found_paths.append(path)
        
        if found_paths:
            print(f"[OK] Found FFmpeg paths:")
            for path in found_paths:
                print(f"   {path}")
        else:
            print("[FAIL] No FFmpeg paths found")
    else:
        print("Non-Windows environment, skipping Windows path detection")
    
    # 测试实际FFmpeg调用
    print("\n5. Actual FFmpeg call test:")
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("[OK] FFmpeg call successful")
            # 提取版本信息
            first_line = result.stdout.split('\n')[0]
            print(f"   Version: {first_line}")
        else:
            print(f"[FAIL] FFmpeg call failed: {result.stderr}")
    except FileNotFoundError:
        print("[FAIL] FFmpeg command not found")
    except subprocess.TimeoutExpired:
        print("[FAIL] FFmpeg call timeout")
    except Exception as e:
        print(f"[FAIL] FFmpeg call exception: {e}")

def test_environment_info():
    """显示环境信息"""
    print("\n=== Environment Info ===")
    print(f"OS: {sys.platform}")
    print(f"Python Version: {sys.version}")
    print(f"Current Directory: {os.getcwd()}")
    print(f"PATH Environment: {os.environ.get('PATH', 'Not set')}")
    print(f"GITHUB_ACTIONS: {os.environ.get('GITHUB_ACTIONS', 'Not set')}")

if __name__ == "__main__":
    test_environment_info()
    test_ffmpeg_detection()
    
    print("\n=== Test Complete ===")
    print("If FFmpeg detection fails, please ensure:")
    print("1. Local environment: Install FFmpeg or check path configuration")
    print("2. GitHub Actions: Ensure FFmpeg is correctly installed in workflow")
    print("3. Path configuration: Check path settings in video_check_worker.py")
