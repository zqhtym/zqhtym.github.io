#!/usr/bin/env python3

# video_check_worker.py - Independent video detection process

import os
import sys
import json
import cv2
import time
import shutil
import threading
import numpy as np
import subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Environment detection
IS_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'

try:
    from pymediainfo import MediaInfo
except ImportError:
    MediaInfo = None
    if IS_GITHUB_ACTIONS:
        print("[GitHub Actions] Warning: pymediainfo not available, will use fallback detection")

# ======================== Global configuration module ========================

class Config:
    """Global configuration class"""

    # Request headers
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # Timeout configuration
    TIMEOUT = {
        'remote_fetch': 10,
        '404_check': 3,
        'speed_test': 5,
        'stream_read': 5,
        'video_check': int(os.environ.get('VIDEO_CHECK_TIMEOUT', 15)),  # Video detection timeout (seconds), configurable via environment variable
        'video_total_timeout': int(os.environ.get('VIDEO_TOTAL_TIMEOUT', 180))  # Video detection total timeout, configurable via environment variable
    }

    # Video detection configuration
    VIDEO_CHECK = {
        'frame_interval': 2,  # Take one frame every 2 seconds (faster sampling)
        'min_diff': 1000,     # Frame difference threshold (significantly lower threshold to adapt to GitHub Actions environment)
        'min_width': 160,     # Minimum effective width (further lower requirements)
        'min_height': 120,    # Minimum effective height (further lower requirements)
        'audio_check': True    # Enable audio detection
    }

# Global variables for timeout control
timeout_flag = False

def check_video_changes(url):
    """Detect screen changes within 15 seconds"""
    result = {
        'success': False,
        'changing': False,
        'reason': '',
        'frame_info': {
            'total_read': 0,
            'valid_frames': 0,
            'avg_diff': 0.0
        }
    }
    
    # Set timeout timer (3 minutes)
    def timeout_handler():
        global timeout_flag
        timeout_flag = True
    
    timer = threading.Timer(Config.TIMEOUT['video_total_timeout'], timeout_handler)
    timer.start()
    
    try:
        # Pre-check 1: 404 detection
        try:
            req = Request(url, headers=Config.HEADERS)
            with urlopen(req, timeout=Config.TIMEOUT['404_check']) as resp:
                if resp.status == 404:
                    reason = f"URL: {url} | Error: 404 Not Found (link invalid)"
                    print(f"[Debug] Screen change detection failed | {reason}")
                    result['reason'] = reason
                    return result
                url_valid = True
        except HTTPError as e:
            if e.code == 404:
                reason = f"URL: {url} | Error: 404 Not Found (link invalid)"
                print(f"[Debug] Screen change detection failed | {reason}")
                result['reason'] = reason
                return result
            url_valid = True  # Non-404 errors (like 500) still attempt to read
        except (URLError, TimeoutError):
            reason = f"URL: {url} | Error: Unable to connect (network timeout/link unreachable)"
            print(f"[Debug] Screen change detection failed | {reason}")
            result['reason'] = reason
            return result

        if not url_valid:
            result['reason'] = f"URL: {url} | Error: URL validation failed"
            return result

        # Pre-check 2: Determine if it's a ts segment (avoid single segment playback issues)
        url_lower = url.lower()
        if url_lower.endswith('.ts'):
            reason = f"URL: {url} | Note: TS segments need to be played through m3u8 index, cannot parse screen individually"
            print(f"[Debug] Detected TS single segment | {reason}")
            result['reason'] = reason
            return result

        # Try to read video stream with retry mechanism
        # Do not use ffmpeg:// prefix in GitHub Actions, use URL directly
        max_retries = 3
        cap = None
        
        for retry in range(max_retries):
            try:
                cap = cv2.VideoCapture(url)
                
                # Set environment variables in GitHub Actions to avoid GUI-related errors
                if IS_GITHUB_ACTIONS:
                    os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
                
                # Set timeout and buffer parameters
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)  # 3-second open timeout (reduced)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)   # 3-second read timeout (reduced)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer size

                if not cap.isOpened():
                    if retry < max_retries - 1:
                        print(f"[Debug] Retry {retry + 1}/{max_retries} - Unable to open video stream | URL: {url}")
                        time.sleep(1)  # Wait before retry
                        continue
                    else:
                        reason = f"URL: {url} | Error: Unable to open video stream after {max_retries} attempts (format not supported/link invalid)"
                        print(f"[Debug] Screen change detection failed | {reason}")
                        result['reason'] = reason
                        if cap:
                            cap.release()
                        return result
                
                # Test if we can actually read a frame
                test_ret, test_frame = cap.read()
                if not test_ret:
                    if retry < max_retries - 1:
                        print(f"[Debug] Retry {retry + 1}/{max_retries} - Cannot read frame, stream may be ending | URL: {url}")
                        cap.release()
                        time.sleep(2)  # Wait longer before retry
                        continue
                    else:
                        reason = f"URL: {url} | Error: Cannot read video frames (stream ended prematurely or format not supported)"
                        print(f"[Debug] Screen change detection failed | {reason}")
                        result['reason'] = reason
                        cap.release()
                        return result
                
                # If we can read a frame, break the retry loop
                print(f"[Debug] Successfully opened video stream on attempt {retry + 1} | URL: {url}")
                break
                
            except Exception as e:
                if retry < max_retries - 1:
                    print(f"[Debug] Retry {retry + 1}/{max_retries} - Exception during open: {str(e)} | URL: {url}")
                    if cap:
                        cap.release()
                    time.sleep(1)
                    continue
                else:
                    reason = f"URL: {url} | Error: Exception during video stream opening: {str(e)}"
                    print(f"[Debug] Screen change detection failed | {reason}")
                    result['reason'] = reason
                    if cap:
                        cap.release()
                    return result

        # 3. Read frames and detect changes (with timeout check)
        frames = []
        start_time = time.time()
        last_frame_time = start_time
        frame_read_count = 0  # Count successfully read frames
        consecutive_failures = 0  # Track consecutive read failures
        max_consecutive_failures = 5  # Max allowed consecutive failures

        while time.time() - start_time < Config.TIMEOUT['video_check']:
            # Check if timeout (3 minutes)
            if timeout_flag:
                reason = f"URL: {url} | Reason: Forced termination after 3 minutes"
                print(f"[Debug] Video detection timeout | {reason}")
                result['reason'] = reason
                cap.release()
                return result

            ret, frame = cap.read()
            if not ret:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    print(f"[Debug] Stream ended after {frame_read_count} frames (consecutive failures: {consecutive_failures}) | URL: {url}")
                    break  # Stream ended or having persistent issues
                else:
                    # Try to continue reading, might be temporary issue
                    time.sleep(0.1)  # Small delay before retry
                    continue
            else:
                consecutive_failures = 0  # Reset failure counter on successful read

            frame_read_count += 1
            current_time = time.time()
            
            # Take one frame at specified intervals (reduce computation)
            if current_time - last_frame_time >= Config.VIDEO_CHECK['frame_interval']:
                try:
                    # Convert to grayscale and shrink
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray = cv2.resize(gray, (320, 240))
                    frames.append(gray)
                    last_frame_time = current_time
                except Exception as e:
                    print(f"[Debug] Frame processing error: {str(e)} | URL: {url}")
                    continue  # Skip this frame but continue with others

            # Take at most 5 frames (enough to determine changes, avoid long time)
            if len(frames) >= 5:
                break

        cap.release()

        # Exception handling
        if frame_read_count == 0:
            reason = f"URL: {url} | Error: No video frames read (possibly invalid stream/format not supported)"
            print(f"[Debug] Screen change detection failed | {reason}")
            result['reason'] = reason
            return result

        if len(frames) < 2:
            reason = f"URL: {url} | Error: Insufficient valid frames (read {frame_read_count} frames total, need at least 2 for comparison)"
            print(f"[Debug] Screen change detection failed | {reason}")
            result['reason'] = reason
            return result

        # Calculate adjacent frame differences
        total_diff = 0
        for i in range(1, len(frames)):
            diff = cv2.absdiff(frames[i-1], frames[i])
            non_zero = np.count_nonzero(diff)
            total_diff += non_zero

        avg_diff = total_diff / (len(frames) - 1)
        is_changing = avg_diff > Config.VIDEO_CHECK['min_diff']

        # Fill success result
        result['success'] = True
        result['changing'] = is_changing
        result['reason'] = "Detection successful"
        result['frame_info'] = {
            'total_read': frame_read_count,
            'valid_frames': len(frames),
            'avg_diff': round(avg_diff, 2)
        }

        # Detect audio before detecting screen changes
        has_audio_detected = False
        try:
            # First, detect FFmpeg version
            version_cmd = ['ffmpeg', '-version']
            version_result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=5)
            ffmpeg_version = version_result.stdout if version_result.returncode == 0 else ""
            
            # Check if FFmpeg supports -select_streams (version 4.4+)
            supports_select_streams = 'ffmpeg version 6.' in ffmpeg_version or 'ffmpeg version 5.' in ffmpeg_version or 'ffmpeg version 4.4' in ffmpeg_version
            
            if supports_select_streams:
                # Use modern FFmpeg command (6.1.1+)
                cmd_audio_modern = [
                    'ffmpeg', '-i', url,
                    '-hide_banner', '-nostats', '-v', 'error',
                    '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1'
                ]
                result_audio = subprocess.run(
                    cmd_audio_modern,
                    capture_output=True,
                    text=True,
                    timeout=15  # 15-second timeout
                )
                
                if result_audio.returncode == 0 and result_audio.stdout.strip():
                    has_audio_detected = True
                    print(f"[Debug] Audio detection successful (modern) | URL: {url}")
                else:
                    # Modern command failed, fallback to legacy parsing
                    cmd_audio_fallback = [
                        'ffmpeg', '-i', url,
                        '-hide_banner'
                    ]
                    result_audio = subprocess.run(
                        cmd_audio_fallback,
                        capture_output=True,
                        text=True,
                        timeout=15  # 15-second timeout
                    )
                    output_audio = result_audio.stderr.strip()  # FFmpeg outputs stream info to stderr
                    if 'Audio:' in output_audio:
                        has_audio_detected = True
                        print(f"[Debug] Audio detection successful (fallback) | URL: {url}")
            else:
                # Use legacy FFmpeg command (4.3.1 compatible)
                cmd_audio_legacy = [
                    'ffmpeg', '-i', url,
                    '-hide_banner'
                ]
                result_audio = subprocess.run(
                    cmd_audio_legacy,
                    capture_output=True,
                    text=True,
                    timeout=15  # 15-second timeout
                )
                output_audio = result_audio.stderr.strip()  # FFmpeg outputs stream info to stderr
                if 'Audio:' in output_audio:
                    has_audio_detected = True
                    print(f"[Debug] Audio detection successful (legacy) | URL: {url}")
                    
        except subprocess.TimeoutExpired:
            print(f"[Debug] Audio detection timeout | URL: {url}")
        except Exception as e:
            print(f"[Debug] Audio detection exception | URL: {url} | Error: {e}")

        # Output JSON format result for easy parsing by external programs
        output_result = {
            'success': True,
            'has_video': True,
            'has_audio': bool(has_audio_detected),  # Convert to Python bool
            'video_changing': bool(is_changing),     # Convert to Python bool
            'changing': bool(is_changing),          # Add backward compatibility
            'error': None
        }

        print(json.dumps(output_result, ensure_ascii=True))
        print(f"[Debug] Screen change detection successful | URL: {url} | Frames read: {frame_read_count} | Valid comparison frames: {len(frames)} | Average frame difference: {avg_diff:.0f} | Changing: {is_changing}")

        return result

    except Exception as e:
        # Check if timeout on exception
        if timeout_flag:
            reason = f"URL: {url} | Reason: Forced termination after 3 minutes"
            print(f"[Debug] Video detection timeout | {reason}")
        else:
            reason = f"URL: {url} | Error: {str(e)}"
            print(f"[Debug] Video detection exception | {reason}")
            import traceback
            traceback.print_exc()

        result['reason'] = reason
        return result

    finally:
        # Stop timer (avoid memory leak)
        timer.cancel()

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
        print(json.dumps(output, ensure_ascii=True))
        sys.exit(1)

    url = sys.argv[1]
    result = check_video_changes(url)

    if not result['success']:
        output_result = {
            'has_video': False,
            'has_audio': False,
            'video_changing': False,
            'error': result['reason']
        }
        print(json.dumps(output_result, ensure_ascii=True))
        sys.exit(1)
    
    sys.exit(0)
