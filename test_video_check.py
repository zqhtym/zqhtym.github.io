#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test video check worker with a sample URL
"""

import subprocess
import json
import os

def test_video_check():
    """Test video check with a sample URL from step5 CSV"""
    # Use a sample URL from the CSV
    test_url = "http://61.221.215.25:8800/hls/49/index.m3u8"
    
    print(f"Testing video check with URL: {test_url}")
    
    try:
        # Call video_check_worker.py
        script_path = 'utils/video_check_worker.py'
        result = subprocess.run([
            'python', script_path, test_url
        ], capture_output=True, timeout=60, text=True)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        
        # Try to parse JSON from output
        try:
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                if line.startswith('{') and line.endswith('}'):
                    json_result = json.loads(line)
                    print(f"\nParsed JSON result:")
                    print(f"  Success: {json_result.get('success', False)}")
                    print(f"  Has video: {json_result.get('has_video', False)}")
                    print(f"  Has audio: {json_result.get('has_audio', False)}")
                    print(f"  Video changing: {json_result.get('video_changing', False)}")
                    if 'error' in json_result:
                        print(f"  Error: {json_result['error']}")
                    break
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            
    except subprocess.TimeoutExpired:
        print("Test timed out after 60 seconds")
    except Exception as e:
        print(f"Test failed with exception: {e}")

if __name__ == "__main__":
    test_video_check()
