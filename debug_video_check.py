#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试画面检测问题
"""

import sys
import os
import json
import subprocess
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_single_url(url):
    """测试单个URL的画面检测"""
    try:
        # 调用video_check_worker.py脚本
        script_path = 'utils/video_check_worker.py'
        result = subprocess.run([
            'python', script_path, url
        ], capture_output=True, timeout=30)  # 30秒超时
        
        if result.returncode == 0:
            # 处理输出编码
            try:
                output = result.stdout.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    output = result.stdout.decode('gbk')
                except UnicodeDecodeError:
                    output = result.stdout.decode('latin1', errors='ignore')
            
            # 查找JSON部分
            start_idx = output.find('{')
            end_idx = output.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = output[start_idx:end_idx + 1]
                video_result = json.loads(json_str)
                return {
                    'url': url,
                    'success': video_result.get('success', False),
                    'changing': video_result.get('changing', False),
                    'reason': video_result.get('reason', ''),
                    'frame_info': video_result.get('frame_info', {}),
                    'stdout': output,
                    'stderr': result.stderr.decode('utf-8', errors='ignore')
                }
            else:
                return {
                    'url': url,
                    'success': False,
                    'changing': False,
                    'reason': f'无法解析JSON输出: {output}',
                    'stdout': output,
                    'stderr': result.stderr.decode('utf-8', errors='ignore')
                }
        else:
            return {
                'url': url,
                'success': False,
                'changing': False,
                'reason': f'脚本执行失败: {result.stderr.decode("utf-8", errors="ignore")}',
                'stdout': result.stdout.decode('utf-8', errors='ignore'),
                'stderr': result.stderr.decode('utf-8', errors='ignore')
            }
    except Exception as e:
        return {
            'url': url,
            'success': False,
            'changing': False,
            'reason': f'测试异常: {str(e)}',
            'stdout': '',
            'stderr': str(e)
        }

def main():
    """主函数"""
    # 读取Step5结果文件
    step5_csv_path = "output1/step5_speed_resources.csv"
    
    if not os.path.exists(step5_csv_path):
        print(f"错误: Step5结果文件不存在：{step5_csv_path}")
        return
    
    # 读取前10个URL进行测试
    test_urls = []
    try:
        with open(step5_csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 简单解析CSV（跳过注释行）
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    url = parts[1].strip()
                    if url.startswith('http'):
                        test_urls.append((name, url))
                        if len(test_urls) >= 10:
                            break
    except Exception as e:
        print(f"错误: 读取CSV文件失败: {e}")
        return
    
    print(f"开始测试前10个URL的画面检测...")
    print("=" * 80)
    
    success_count = 0
    changing_count = 0
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for name, url in test_urls:
            print(f"\n测试: {name}")
            print(f"URL: {url}")
            
            future = executor.submit(test_single_url, url)
            futures.append((name, future))
        
        for name, future in futures:
            result = future.result()
            
            print(f"\n结果: {name}")
            print(f"   成功: {result['success']}")
            print(f"   画面变化: {result['changing']}")
            print(f"   原因: {result['reason']}")
            
            if result['success']:
                success_count += 1
                if result['changing']:
                    changing_count += 1
                    
                frame_info = result.get('frame_info', {})
                if frame_info:
                    print(f"   帧信息: {frame_info}")
            
            if result.get('stderr'):
                print(f"   错误输出: {result['stderr'][:200]}...")
    
    print("\n" + "=" * 80)
    print(f"测试统计:")
    print(f"   总测试数: {len(test_urls)}")
    print(f"   检测成功: {success_count}")
    print(f"   画面变化: {changing_count}")
    print(f"   成功率: {success_count/len(test_urls)*100:.1f}%")
    print(f"   变化率: {changing_count/len(test_urls)*100:.1f}%")

if __name__ == "__main__":
    main()
