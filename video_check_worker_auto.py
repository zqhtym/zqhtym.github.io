#!/usr/bin/env python3
# video_check_worker_auto.py - 自动检测环境并选择合适的画面检测策略

import os
import sys
import json
import subprocess

def detect_environment():
    """检测运行环境"""
    env_info = {
        'is_github_actions': False,
        'is_local': False,
        'network_type': 'unknown',
        'has_ffmpeg': False
    }
    
    # 检测是否为GitHub Actions环境
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        env_info['is_github_actions'] = True
        env_info['network_type'] = 'external'
        print("[环境检测] 检测到GitHub Actions环境")
    else:
        env_info['is_local'] = True
        env_info['network_type'] = 'internal'
        print("[环境检测] 检测到本地环境")
    
    # 检测FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=5)
        env_info['has_ffmpeg'] = True
        print("[环境检测] FFmpeg可用")
    except:
        print("[环境检测] FFmpeg不可用")
    
    return env_info

def check_video_changes_auto(url):
    """自动选择合适的画面检测策略"""
    env_info = detect_environment()
    
    if env_info['is_github_actions']:
        print("[策略选择] 使用GitHub Actions优化策略")
        # 导入GitHub Actions版本
        from video_check_worker_github import check_video_changes_github
        return check_video_changes_github(url)
    else:
        print("[策略选择] 使用标准策略")
        # 导入标准版本
        from video_check_worker import check_video_changes
        return check_video_changes(url)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        output = {
            'success': False,
            'reason': 'invalid_args',
            'changing': False,
            'frame_info': {
                'total_read': 0,
                'valid_frames': 0,
                'avg_diff': 0.0
            }
        }
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(1)
    
    url = sys.argv[1]
    result = check_video_changes_auto(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)
