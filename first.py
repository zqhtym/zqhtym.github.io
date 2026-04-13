#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV Resource Processing Pipeline - Complete Version
Step1: Load all resources with interactive URL processing
"""

import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import csv
import asyncio
import aiohttp
import os
import re
import requests
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from multiprocessing import Manager
from functools import partial
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def decode_unicode_escapes(text):
    """
    Decode Unicode escape sequences like \\u53d1\\u73b0\\u4e4b\\u65c5
    Enhanced with multiple fallback methods for robust decoding
    Also handles double backslash issues from file storage
    """
    if not text:
        return text
    
    original = text
    
    # CRITICAL FIX: Handle double backslash issue from file storage
    # Convert \\\\uXXXX to \\uXXXX for proper decoding
    if '\\\\u' in text:
        text = text.replace('\\\\u', '\\u')
    
    # Method 1: Direct codecs.decode (most reliable)
    try:
        import codecs
        decoded = codecs.decode(text, 'unicode_escape')
        # Verify it worked by checking for remaining escapes
        if '\\u' not in decoded:
            return decoded
    except:
        pass
    
    # Method 2: Manual regex replacement (more robust)
    try:
        import re
        unicode_pattern = re.compile(r'\\u([0-9a-fA-F]{4})')
        def replace_unicode(match):
            try:
                char_code = int(match.group(1), 16)
                return chr(char_code)
            except:
                return match.group(0)
        
        decoded = unicode_pattern.sub(replace_unicode, text)
        
        # Method 3: Handle double-encoded cases
        if '\\u' in decoded:
            try:
                decoded = codecs.decode(decoded, 'unicode_escape')
            except:
                # Apply regex again
                decoded = unicode_pattern.sub(replace_unicode, decoded)
        
        # Return if successful
        if '\\u' not in decoded:
            return decoded
            
    except:
        pass
    
    # If all methods fail, return original
    return original

def convert_to_simplified_chinese(text):
    """
    Convert Traditional Chinese to Simplified Chinese
    """
    if not text:
        return text
    
    # Traditional to Simplified Chinese mapping
    trad_to_simp = {
        'CCTV': 'CCTV',
        'CCTV': 'CCTV',
    }
    
    # Apply conversions
    for trad, simp in trad_to_simp.items():
        text = text.replace(trad, simp)
    
    return text

def validate_chinese_decoding(text, original_text):
    """
    Validate that Chinese decoding was successful
    Returns: (is_valid, fixed_text, validation_details)
    """
    if not text:
        return True, text, "Empty text"
    
    validation_details = []
    unicode_escapes_before = original_text.count('\\u')
    unicode_escapes_after = text.count('\\u')
    
    # CRITICAL: Any remaining Unicode escapes make it invalid
    if unicode_escapes_after > 0:
        validation_details.append(f"Unicode escapes remaining: {unicode_escapes_after}")
        return False, text, f"FAILED: Unicode escapes not fully decoded: {unicode_escapes_after} remaining"
    
    # Check if Unicode escapes were successfully decoded
    if unicode_escapes_before > 0 and unicode_escapes_after == 0:
        validation_details.append(f"Unicode escapes decoded: {unicode_escapes_before}")
    
    # Check for Chinese characters (this is good)
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    if chinese_chars > 0:
        validation_details.append(f"Chinese chars found: {chinese_chars}")
    
    # Check for common encoding issues (these are bad)
    encoding_issues = ['å', 'ä', 'ö', 'Ã', 'Â', 'â', '¬', '¦', '§', '¨']
    found_issues = [char for char in encoding_issues if char in text]
    if found_issues:
        validation_details.append(f"Encoding issues found: {found_issues}")
        return False, text, f"FAILED: Encoding issues remain: {found_issues}"
    
    # If no Unicode escapes remain, it's valid
    return True, text, "; ".join(validation_details) if validation_details else "Valid"

def fix_chinese_encoding(text):
    """
    Fix Chinese encoding issues with comprehensive decoding and conversion
    Enhanced with stronger Unicode escape handling and double backslash fix
    """
    if not text:
        return text
    
    original_text = text
    
    # CRITICAL FIX: Handle double backslash issue from file storage
    # Convert \\\\uXXXX to \\uXXXX for proper decoding
    if '\\\\u' in text:
        text = text.replace('\\\\u', '\\u')
    
    # Step 1: Priority - Decode Unicode escape sequences
    if '\\u' in text:
        try:
            import codecs
            decoded = codecs.decode(text, 'unicode_escape')
            text = decoded
        except Exception as e:
            # If direct decode fails, try manual approach
            import re
            unicode_pattern = re.compile(r'\\u([0-9a-fA-F]{4})')
            def replace_unicode(match):
                try:
                    return chr(int(match.group(1), 16))
                except:
                    return match.group(0)
            text = unicode_pattern.sub(replace_unicode, text)
    
    # Step 2: Try to fix encoding issues
    try:
        # Check if it's mis-encoded Chinese (contains å, ä, ö)
        if 'å' in text or 'ä' in text or 'ö' in text:
            # Try to decode as latin-1 and encode as utf-8
            try:
                fixed = text.encode('latin-1').decode('utf-8')
                text = fixed
            except:
                pass
        
        # Try other common encoding fixes
        try:
            fixed = text.encode('cp1252').decode('utf-8')
            text = fixed
        except:
            pass
            
        try:
            fixed = text.encode('iso-8859-1').decode('utf-8')
            text = fixed
        except:
            pass
            
        # Try to detect if it's double-encoded
        try:
            # Try to decode as bytes then encode as utf-8
            fixed = text.encode('raw_unicode_escape').decode('utf-8')
            text = fixed
        except:
            pass
            
    except:
        pass
    
    # Step 3: Convert to Simplified Chinese
    text = convert_to_simplified_chinese(text)
    
    # Step 4: Validate the decoding
    is_valid, validated_text, details = validate_chinese_decoding(text, original_text)
    
    return validated_text

class IPTVResourceProcessor:
    """ IPTV Resource Processing Pipeline """
    
    def __init__(self):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    async def run_step1_only(self):
        """ Run Step1 only: Load all IPTV resources """
        print("="*80)
        print(f"IPTV Resource Processing - Step1 Only: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        start_time = time.time()
        
        # Load resources from all sources with smart merging
        all_resources = {}
        
        # Load local M3U resources
        print("\n Step1: Loading all IPTV resources...")
        local_m3u_resources = await self._load_local_m3u("resources.m3u")
        all_resources.update(local_m3u_resources)
        print(f"  Loaded {len(local_m3u_resources)} resources from resources.m3u")
        
        # Load local TXT resources
        local_txt_resources = await self._load_local_txt("resources.txt")
        all_resources.update(local_txt_resources)
        print(f"  Loaded {len(local_txt_resources)} resources from resources.txt")
        
        # Load remote resources with interactive processing
        remote_resources = await self._load_local_remote_resources("resources_remote.txt")
        
        # SMART MERGE: Prevent Unicode sequences from overwriting decoded data
        print("  Smart merging remote resources...")
        merged_count = 0
        skipped_unicode_count = 0
        
        # FINAL PROTECTION: Create a set of decoded channel names to protect
        protected_names = set()
        for name in all_resources.keys():
            if '\\u' not in name:
                # This is a properly decoded name, protect it
                protected_names.add(name)
        
        print(f"  Protected {len(protected_names)} decoded channel names")
        
        for name, urls in remote_resources.items():
            # CRITICAL FIX: Check if this remote entry would overwrite decoded local data
            if '\\u' in name:
                # Try to decode this name to see what it should be
                try:
                    decoded_name = fix_chinese_encoding(name)
                    if '\\u' not in decoded_name:
                        # Check if the decoded version already exists in protected names
                        if decoded_name in protected_names:
                            print(f"    PROTECTED: Adding Unicode entry to existing decoded data: {name} -> {decoded_name}")
                            # Instead of skipping, append to existing decoded name
                            name = decoded_name
                        else:
                            print(f"    Safe to add decoded: {name} -> {decoded_name}")
                            # Use decoded name for merging
                            name = decoded_name
                    else:
                        # Still has Unicode escapes, keep original but log it
                        print(f"    Keeping entry with unresolved Unicode escapes: {name}")
                        # Keep original name - don't skip
                except:
                    # If decoding fails, keep original but log it
                    print(f"    Keeping entry with decoding error: {name}")
                    # Keep original name - don't skip
            
            # Normal merge logic - keep all URLs including duplicates
            if name in all_resources:
                # Instead of extending (which merges), append all URLs to keep duplicates
                all_resources[name].extend(urls)
            else:
                all_resources[name] = urls
            merged_count += 1
        
        print(f"  Merged {merged_count} remote resources")
        print(f"  Skipped {skipped_unicode_count} entries with Unicode issues")
        
        # FINAL CLEANUP: Force decode all Unicode sequences before saving
        print("  Final cleanup: Force decoding all remaining Unicode sequences...")
        cleanup_count = 0
        final_resources = {}
        
        for name, urls in all_resources.items():
            # Check if this name has Unicode sequences
            if '\\u' in name:
                try:
                    # Force decode using multiple methods
                    decoded_name = fix_chinese_encoding(name)
                    
                    # If still has Unicode, try more aggressive decoding
                    if '\\u' in decoded_name:
                        import codecs
                        try:
                            # Try direct codecs.decode
                            decoded_name = codecs.decode(decoded_name, 'unicode_escape')
                        except:
                            # Try manual regex replacement
                            import re
                            unicode_pattern = re.compile(r'\\u([0-9a-fA-F]{4})')
                            def replace_unicode(match):
                                try:
                                    return chr(int(match.group(1), 16))
                                except:
                                    return match.group(0)
                            decoded_name = unicode_pattern.sub(replace_unicode, decoded_name)
                    
                    # Use the decoded name
                    if decoded_name in final_resources:
                        final_resources[decoded_name].extend(urls)
                    else:
                        final_resources[decoded_name] = urls
                    cleanup_count += 1
                    print(f"    Force decoded: {name} -> {decoded_name}")
                    
                except Exception as e:
                    # If all decoding fails, use original but log it
                    print(f"    WARNING: Could not decode {name}: {e}")
                    if name in final_resources:
                        final_resources[name].extend(urls)
                    else:
                        final_resources[name] = urls
            else:
                # Normal name, keep as is
                if name in final_resources:
                    final_resources[name].extend(urls)
                else:
                    final_resources[name] = urls
        
        print(f"  Force decoded {cleanup_count} entries with Unicode sequences")
        print(f"  Final total: {len(final_resources)} channels")
        
        # Replace all_resources with cleaned version
        all_resources = final_resources
        
        # Save all resources to CSV
        csv_path = self.output_dir / "step1_all_resources.csv"
        await self._save_resources_to_csv(all_resources, csv_path)
        
        # Print completion summary
        await self._print_step1_summary(all_resources, start_time)
        
        print(f"\n Step1 completed! Total time: {self._format_duration(time.time() - start_time)}")
    
    async def _load_local_m3u(self, filepath):
        """ Load resources from local M3U file """
        resources = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_name = ""
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('#EXTINF:'):
                    # Extract channel name from M3U format
                    name_match = re.search(r',(.*?)$', line)
                    if name_match:
                        original_name = name_match.group(1).strip()
                        fixed_name = fix_chinese_encoding(original_name)
                        current_name = fixed_name
                        
                elif line.startswith('http') and current_name:
                    # This is a URL line following #EXTINF
                    if current_name not in resources:
                        resources[current_name] = []
                    resources[current_name].append(line)
                    current_name = ""
                    
                elif line.startswith('http') and not current_name:
                    # Format: pure URL
                    name = f"Local_M3U_{len(resources)+1}"
                    if name not in resources:
                        resources[name] = []
                    resources[name].append(line)
        
        except FileNotFoundError:
            print(f"  Warning: {filepath} not found")
        except Exception as e:
            print(f"  Error loading {filepath}: {e}")
        
        return resources
    
    async def _load_local_txt(self, filepath):
        """ Load resources from local TXT file """
        resources = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#genre#'):
                    continue
                
                if ',' in line:
                    # Format: name,url
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        original_name = parts[0].strip()
                        fixed_name = fix_chinese_encoding(original_name)
                        url = parts[1].strip()
                        if url.startswith('http'):
                            if fixed_name not in resources:
                                resources[fixed_name] = []
                            resources[fixed_name].append(url)
                            
                elif line.startswith('http'):
                    # Format: pure URL
                    name = f"Local_TXT_{len(resources)+1}"
                    if name not in resources:
                        resources[name] = []
                    resources[name].append(line)
        
        except FileNotFoundError:
            print(f"  Warning: {filepath} not found")
        except Exception as e:
            print(f"  Error loading {filepath}: {e}")
        
        return resources
    
    async def _load_local_remote_resources(self, filepath):
        """ Load resources from local file containing remote URLs to download """
        resources = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Check if we're in interactive mode
            interactive_mode = sys.stdin.isatty()
            
            print(f"\n===  Step1  -   Remote URL Processing  ===")
            print(f"Found {len([l for l in lines if l.strip().startswith('http')])} remote URLs to process")
            
            if interactive_mode:
                print(f"Each URL will be processed individually with your confirmation\n")
                print("Commands: Enter=process, skip=skip URL, quit=exit, auto=auto-mode")
            else:
                print("Non-interactive mode detected: Processing all URLs automatically")
                auto_mode = True
            
            url_count = 0
            auto_mode = not interactive_mode
            
            for line in lines:
                line = line.strip()
                if line.startswith('http'):
                    url_count += 1
                    
                    # Display URL information and wait for user confirmation
                    print(f"\n{'='*60}")
                    print(f"URL #{url_count}: {line}")
                    print(f"{'='*60}")
                    
                    # Extract resource name from URL for better identification
                    resource_name = self._extract_resource_name_from_url(line)
                    print(f"Resource Name: {resource_name}")
                    
                    # Wait for user confirmation (if in interactive mode)
                    user_input = ''
                    if not auto_mode:
                        try:
                            while True:
                                user_input = input(f"\nPress Enter to process, 'skip' to skip, 'quit' to exit, 'auto' for auto-mode: ").strip().lower()
                                if user_input == '':
                                    break
                                elif user_input == 'skip':
                                    print(f"    Skipped {line} (user skipped)")
                                    auto_mode = False  # Continue to next URL
                                    break
                                elif user_input == 'quit':
                                    print(f"    User requested to quit after processing {url_count-1} URLs")
                                    return resources
                                elif user_input == 'auto':
                                    print("    Switching to auto-mode: Processing remaining URLs automatically")
                                    auto_mode = True
                                    break
                                else:
                                    print("Invalid input. Press Enter to process, 'skip' to skip, 'quit' to exit, 'auto' for auto-mode.")
                        except (EOFError, KeyboardInterrupt):
                            print("\n    Input interrupted. Switching to auto-mode...")
                            auto_mode = True
                    
                    # Skip to next URL if user chose to skip
                    if not auto_mode and user_input == 'skip':
                        continue
                    
                    # Process the URL
                    try:
                        print(f"\n    Processing URL: {line}")
                        
                        # Download the remote URL file with proper headers
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                        response = requests.get(line, headers=headers, timeout=30)
                        response.raise_for_status()
                        
                        # Check content type to skip non-playlist files
                        content_type = response.headers.get('content-type', '').lower()
                        if 'video/' in content_type or 'audio/' in content_type:
                            print(f"    Including {line} (binary media file - keeping as requested)")
                            # Don't skip - keep all URLs as requested
                        
                        # Parse the downloaded content with enhanced encoding handling
                        try:
                            text_content = None
                            remote_lines = []
                            best_encoding = None
                            
                            # Try different encodings with comprehensive detection
                            for encoding in ['utf-8', 'gbk', 'gb2312', 'big5', 'gb18030']:
                                try:
                                    candidate_content = response.content.decode(encoding)
                                    candidate_lines = candidate_content.split('\n')
                                    
                                    # Test if this encoding worked by multiple criteria
                                    test_sample = candidate_lines[:5] if candidate_lines else []
                                    chinese_char_count = 0
                                    unicode_escape_count = 0
                                    
                                    for test_line in test_sample:
                                        # Count Chinese characters
                                        chinese_char_count += sum(1 for char in test_line if '\u4e00' <= char <= '\u9fff')
                                        # Count Unicode escape sequences
                                        unicode_escape_count += test_line.count('\\u')
                                    
                                    # Score this encoding (higher is better)
                                    score = chinese_char_count * 10 + unicode_escape_count * 5
                                    
                                    if score > 0:  # Found Chinese or Unicode escapes
                                        if text_content is None or score > best_encoding.get('score', 0):
                                            text_content = candidate_content
                                            remote_lines = candidate_lines
                                            best_encoding = {'encoding': encoding, 'score': score}
                                            
                                except UnicodeDecodeError:
                                    print(f"    Including {line} despite Unicode decode error - keeping as requested")
                                    # Don't skip - keep all URLs as requested
                            
                            # If no good encoding found, try with error handling
                            if text_content is None:
                                text_content = response.content.decode('utf-8', errors='ignore')
                                remote_lines = text_content.split('\n')
                                best_encoding = {'encoding': 'utf-8', 'score': 0}
                            
                            print(f"    Using encoding: {best_encoding['encoding']} (score: {best_encoding.get('score', 0)})")
                            
                        except Exception as e:
                            print(f"    Including {line} despite encoding error: {e} - keeping as requested")
                            # Don't skip - keep all URLs as requested
                        
                        # Check if content is actually a playlist (M3U or TXT format)
                        is_playlist = False
                        for check_line in remote_lines[:50]:  # Check first 50 lines
                            check_line = check_line.strip()
                            if check_line.startswith('#EXTM3U') or check_line.startswith('#EXTINF:'):
                                is_playlist = True
                                break
                            elif check_line.startswith('http') and ',' in check_line:
                                is_playlist = True
                                break
                            elif ',' in check_line and not check_line.startswith('#') and not check_line.startswith('http'):
                                # Check if it's name,url format
                                parts = check_line.split(',', 1)
                                if len(parts) == 2 and parts[1].strip().startswith('http'):
                                    is_playlist = True
                                    break
                        
                        if not is_playlist and 'text/html' in content_type:
                            print(f"    Including {line} (HTML page - keeping as requested)")
                            # Don't skip - keep all URLs as requested
                        elif not is_playlist:
                            print(f"    Including {line} (not a playlist format - keeping as requested)")
                            # Don't skip - keep all URLs as requested
                        
                        # Process each line with strict validation
                        channel_count = 0
                        current_name = ""
                        decoded_channels = 0
                        unicode_fixed = 0
                        trad_to_simp = 0
                        validation_errors = 0
                        validation_success = 0
                        
                        print(f"    Processing {len(remote_lines)} lines with strict validation...")
                        
                        for line_num, remote_line in enumerate(remote_lines, 1):
                            remote_line = remote_line.strip()
                            if not remote_line or remote_line.startswith('#genre#'):
                                continue
                            
                            original_name = ""
                            fixed_name = ""
                            
                            if remote_line.startswith('#EXTINF:'):
                                # Extract channel name from M3U format
                                name_match = re.search(r',(.*?)$', remote_line)
                                if name_match:
                                    original_name = name_match.group(1).strip()
                                    fixed_name = fix_chinese_encoding(original_name)
                                    current_name = fixed_name
                                    
                                    # Validate decoding for this channel name
                                    is_valid, validated_name, validation_details = validate_chinese_decoding(fixed_name, original_name)
                                    
                                    if is_valid:
                                        validation_success += 1
                                        current_name = validated_name  # Use validated name
                                        if original_name != fixed_name:
                                            if '\\u' in original_name:
                                                unicode_fixed += 1
                                            else:
                                                trad_to_simp += 1
                                    else:
                                        validation_errors += 1
                                        print(f"      Line {line_num}: Decoding validation failed - {validation_details}")
                                        # CRITICAL: Do NOT use any name that has Unicode escapes
                                        if '\\u' in original_name:
                                            print(f"      Line {line_num}: SKIPPING channel with Unicode escapes: {original_name}")
                                            current_name = None  # Skip this channel entirely
                                        else:
                                            current_name = original_name  # Use original if no Unicode escapes
                                            
                            elif remote_line.startswith('http') and current_name:
                                # This is a URL line following #EXTINF
                                # Only process if current_name is valid (not None)
                                if current_name is not None:
                                    if current_name not in resources:
                                        resources[current_name] = []
                                    resources[current_name].append(remote_line)
                                    channel_count += 1
                                    decoded_channels += 1
                                current_name = ""
                            elif ',' in remote_line and not remote_line.startswith('http') and not remote_line.startswith('#'):
                                # Format: name,url
                                parts = remote_line.split(',', 1)
                                if len(parts) == 2:
                                    original_name = parts[0].strip()
                                    fixed_name = fix_chinese_encoding(original_name)
                                    url = parts[1].strip()
                                    if url.startswith('http'):
                                        # Validate decoding for this channel name
                                        is_valid, validated_name, validation_details = validate_chinese_decoding(fixed_name, original_name)
                                        
                                        if is_valid:
                                            validation_success += 1
                                            if validated_name not in resources:
                                                resources[validated_name] = []
                                            resources[validated_name].append(url)
                                            channel_count += 1
                                            decoded_channels += 1
                                            
                                            # Track decoding statistics
                                            if original_name != fixed_name:
                                                if '\\u' in original_name:
                                                    unicode_fixed += 1
                                                else:
                                                    trad_to_simp += 1
                                        else:
                                            validation_errors += 1
                                            print(f"      Line {line_num}: Decoding validation failed - {validation_details}")
                                            # CRITICAL: Do NOT use any name that has Unicode escapes
                                            if '\\u' in original_name:
                                                print(f"      Line {line_num}: SKIPPING channel with Unicode escapes: {original_name}")
                                                # Skip this channel entirely - do not add to resources
                                            else:
                                                # Use original name if no Unicode escapes
                                                if original_name not in resources:
                                                    resources[original_name] = []
                                                resources[original_name].append(url)
                                                channel_count += 1
                                                decoded_channels += 1
                                            
                            elif remote_line.startswith('http') and not current_name:
                                # Format: pure URL
                                name = f"Remote_{len(resources)+1}"
                                if name not in resources:
                                    resources[name] = []
                                resources[name].append(remote_line)
                                channel_count += 1
                                decoded_channels += 1
                                validation_success += 1  # No decoding needed for pure URLs
                        
                        # Print detailed decoding statistics with validation results
                        stats_msg = f"    Downloaded {channel_count} resources from {line}"
                        if unicode_fixed > 0:
                            stats_msg += f" (Unicode fixed: {unicode_fixed})"
                        if trad_to_simp > 0:
                            stats_msg += f" (Trad->Simp: {trad_to_simp})"
                        
                        # Add validation results
                        total_validations = validation_success + validation_errors
                        if total_validations > 0:
                            validation_rate = (validation_success / total_validations) * 100
                            stats_msg += f" (Validation: {validation_success}/{total_validations} = {validation_rate:.1f}%)"
                            if validation_errors > 0:
                                stats_msg += f" [ERRORS: {validation_errors}]"
                        
                        print(stats_msg)
                        
                        # Critical validation check - if too many errors, warn user
                        if total_validations > 0 and validation_errors > 0:
                            error_rate = (validation_errors / total_validations) * 100
                            if error_rate > 10:  # More than 10% validation errors
                                print(f"    WARNING: High validation error rate ({error_rate:.1f}%) - decoding may be incomplete")
                        
                        # Show sample decoded channels
                        if decoded_channels > 0:
                            print(f"    Sample decoded channels:")
                            sample_count = 0
                            for channel_name in list(resources.keys())[-3:]:
                                if sample_count >= 3:
                                    break
                                try:
                                    print(f"      - {channel_name}")
                                    sample_count += 1
                                except UnicodeEncodeError:
                                    print(f"      - [Chinese channel name]")
                                    sample_count += 1
                    
                    except Exception as e:
                        print(f"    Including {line} despite download failure: {e} - keeping as requested")
                        # Don't skip - keep all URLs as requested
                    
                    print(f"    Completed processing URL #{url_count}")
                    print(f"    Total resources collected so far: {len(resources)}")
                    
                    # Brief pause in interactive mode to let user see results
                    if not auto_mode and interactive_mode:
                        time.sleep(1)
        
        except Exception as e:
            print(f"  Error loading local remote resources file {filepath}: {e}")
        
        return resources
    
    def _extract_resource_name_from_url(self, url):
        """Extract a descriptive name from URL for user identification"""
        try:
            # Remove protocol and www
            clean_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
            
            # Extract domain
            if '/' in clean_url:
                domain = clean_url.split('/')[0]
            else:
                domain = clean_url
            
            # Extract filename or path
            if '/' in clean_url:
                path_parts = clean_url.split('/')
                filename = path_parts[-1] if path_parts[-1] else path_parts[-2]
            else:
                filename = 'root'
            
            # Clean up common patterns
            if 'github' in domain:
                if 'raw' in url:
                    return f"GitHub: {filename}"
                else:
                    return f"GitHub Repository"
            elif 'gitee' in domain:
                return f"Gitee: {filename}"
            elif 'live' in domain:
                return f"Live Source: {domain}"
            elif 'tv' in domain:
                return f"TV Source: {domain}"
            elif 'iptv' in domain:
                return f"IPTV: {filename}"
            else:
                return f"Remote: {domain}/{filename}"
                
        except:
            return f"Remote Source"
    
    async def _save_resources_to_csv(self, resources, csv_path):
        """ Save resources to CSV file """
        try:
            with open(csv_path, 'w', encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['resource_name', 'url'])
                
                for name, urls in resources.items():
                    for url in urls:
                        writer.writerow([name, url])
            
            print(f" Saved file: {csv_path}")
            
            # Count valid URLs
            total_urls = sum(len(urls) for urls in resources.values())
            print(f" Valid URLs: {total_urls}/{total_urls}")
            
        except Exception as e:
            print(f"  Error saving CSV: {e}")
    
    async def _print_step1_summary(self, resources, start_time):
        """ Print Step1 completion summary """
        print("\n" + "="*60)
        print("Step1 Resource Loading - Completion Summary")
        print("="*60)
        
        total_channels = len(resources)
        total_urls = sum(len(urls) for urls in resources.values())
        
        print(f"Total Categories: {total_channels}")
        print(f"Total Channels: {total_channels}")
        print(f"Total URLs: {total_urls}")
        
        # Show sample channels
        if resources:
            print("\nSample channels:")
            sample_channels = list(resources.keys())[:5]
            for i, channel in enumerate(sample_channels, 1):
                try:
                    url_count = len(resources[channel])
                    print(f"  {i}. {channel} ({url_count} URLs)")
                except UnicodeEncodeError:
                    print(f"  {i}. [Chinese channel] ({len(resources[channel])} URLs)")
    
    async def run_step2_deblack_deannotation(self):
        """Step2: 过滤black.txt网址特征和按IPTV规则去掉URL注释部分"""
        try:
            print("=" * 80)
            print(f" IPTV Resource Processing - Step2: De-black & De-annotation")
            print("=" * 80)
            
            print("\n[Step2] Loading Step1 output and performing de-black & de-annotation...")
            
            # 读取Step1的输出文件
            step1_file = self.output_dir / "step1_all_resources.csv"
            if not step1_file.exists():
                print(f"  Error: Step1 output file not found: {step1_file}")
                print("  Please run Step1 first using: python first.py --step1")
                return
            
            # 加载black.txt文件
            black_patterns = []
            black_file = Path("black.txt")
            if black_file.exists():
                print(f"  Loading black list: {black_file}")
                with open(black_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            black_patterns.append(line.lower())
                print(f"  Loaded {len(black_patterns)} black patterns")
            else:
                print(f"  Warning: black.txt not found, skipping black filtering")
            
            # 加载所有资源
            all_resources = []
            total_urls_before = 0
            black_filtered = 0
            annotation_removed = 0
            
            print(f"  Loading Step1 output: {step1_file}")
            with open(step1_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    if len(row) >= 2:
                        name = row[0]
                        url = row[1]
                        total_urls_before += 1
                        
                        # 1. 过滤black.txt网址特征
                        is_blacklisted = False
                        if black_patterns:
                            url_lower = url.lower()
                            for pattern in black_patterns:
                                if pattern in url_lower:
                                    is_blacklisted = True
                                    break
                        
                        if is_blacklisted:
                            black_filtered += 1
                            continue
                        
                        # 2. 按IPTV规则去掉URL注释部分（$及以后内容）
                        original_url = url
                        if '$' in url:
                            url = url.split('$')[0]
                            annotation_removed += 1
                        
                        # 添加到结果列表
                        all_resources.append({
                            'name': name,
                            'url': url,
                            'original_url': original_url
                        })
            
            print(f"  Loaded {len(all_resources)} channels")
            print(f"  Total URLs before filtering: {total_urls_before}")
            print(f"  Black-list filtered: {black_filtered}")
            print(f"  Annotations removed: {annotation_removed}")
            
            # 保存Step2结果
            step2_file = self.output_dir / "step2_deblack_deAnnotation.csv"
            self._save_step2_output(all_resources, step2_file)
            
            # 打印摘要
            self._print_step2_summary(all_resources, total_urls_before, black_filtered, annotation_removed)
            
        except Exception as e:
            print(f"  Error in Step2: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_step2_output(self, resources, filepath):
        """保存Step2去黑名单和去注释后的输出文件"""
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['resource_name', 'url'])
                
                for resource in resources:
                    writer.writerow([resource['name'], resource['url']])
            
            print(f"  Saved file: {filepath}")
            
            # Count valid URLs
            total_urls = len(resources)
            print(f"  Valid URLs: {total_urls}")
            
        except Exception as e:
            print(f"  Error saving Step2 CSV: {e}")
    
    def _print_step2_summary(self, resources, urls_before, black_filtered, annotation_removed):
        """打印Step2完成摘要"""
        print("\n" + "="*60)
        print("Step2 De-black & De-annotation - Completion Summary")
        print("="*60)
        
        total_channels = len(resources)
        total_urls_after = len(resources)
        
        print(f"Total Channels: {total_channels}")
        print(f"URLs Before Filtering: {urls_before}")
        print(f"URLs After Filtering: {total_urls_after}")
        print(f"Black-list Filtered: {black_filtered}")
        print(f"Annotations Removed: {annotation_removed}")
        
        if urls_before > 0:
            black_rate = (black_filtered / urls_before * 100)
            annotation_rate = (annotation_removed / urls_before * 100)
            total_removed = black_filtered + annotation_removed
            total_rate = (total_removed / urls_before * 100)
            
            print(f"Black-filter Rate: {black_rate:.2f}%")
            print(f"Annotation Rate: {annotation_rate:.2f}%")
            print(f"Total Filter Rate: {total_rate:.2f}%")
        
        # Show sample channels
        if resources:
            print("\nSample channels:")
            sample_channels = resources[:5]
            for i, channel in enumerate(sample_channels, 1):
                try:
                    name = channel['name']
                    url = channel['url']
                    print(f"  {i}. {name}")
                    print(f"     URL: {url[:80]}{'...' if len(url) > 80 else ''}")
                except UnicodeEncodeError:
                    print(f"  {i}. [Chinese channel]")
    
    async def run_step3_deduplicate(self):
        """Step3: URL去重处理"""
        try:
            print("=" * 80)
            print(f" IPTV Resource Processing - Step3: URL Deduplication")
            print("=" * 80)
            
            print("\n[Step3] Loading Step2 output and performing URL deduplication...")
            
            # 读取Step2的输出文件
            step2_file = self.output_dir / "step2_deblack_deAnnotation.csv"
            if not step2_file.exists():
                print(f"  Error: Step2 output file not found: {step2_file}")
                print("  Please run Step2 first using: python first.py --step2")
                return
            
            # 加载所有资源
            all_resources = {}
            total_urls_before = 0
            duplicate_urls = 0
            
            print(f"  Loading Step2 output: {step2_file}")
            with open(step2_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    if len(row) >= 2:
                        name = row[0]
                        url = row[1]
                        total_urls_before += 1
                        
                        if name not in all_resources:
                            all_resources[name] = set()  # 使用set来去重
                        
                        # 检查URL是否已存在
                        if url in all_resources[name]:
                            duplicate_urls += 1
                        else:
                            all_resources[name].add(url)
            
            print(f"  Loaded {len(all_resources)} channels")
            print(f"  Total URLs before deduplication: {total_urls_before}")
            print(f"  Duplicate URLs found: {duplicate_urls}")
            
            # 转换set回list
            unique_resources = {}
            total_urls_after = 0
            
            for name, url_set in all_resources.items():
                unique_resources[name] = list(url_set)
                total_urls_after += len(url_set)
            
            removed_urls = total_urls_before - total_urls_after
            print(f"  Total URLs after deduplication: {total_urls_after}")
            print(f"  URLs removed: {removed_urls}")
            print(f"  Deduplication rate: {(removed_urls/total_urls_before*100):.2f}%")
            
            # 保存去重后的结果
            step3_file = self.output_dir / "step3_unique_resources.csv"
            self._save_step3_output(unique_resources, step3_file)
            
            # 打印摘要
            self._print_step3_summary(unique_resources, total_urls_before, total_urls_after, removed_urls)
            
        except Exception as e:
            print(f"  Error in Step3: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_step3_output(self, resources, filepath):
        """保存Step3去重后的输出文件"""
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['resource_name', 'url'])
                
                for name, urls in resources.items():
                    for url in urls:
                        writer.writerow([name, url])
            
            print(f" Saved file: {filepath}")
            
            # Count valid URLs
            total_urls = sum(len(urls) for urls in resources.values())
            print(f" Valid URLs: {total_urls}/{total_urls}")
            
        except Exception as e:
            print(f"  Error saving Step3 CSV: {e}")
    
    def _print_step3_summary(self, resources, urls_before, urls_after, removed_urls):
        """打印Step3完成摘要"""
        print("\n" + "="*60)
        print("Step3 URL Deduplication - Completion Summary")
        print("="*60)
        
        total_channels = len(resources)
        
        print(f"Total Channels: {total_channels}")
        print(f"URLs Before Deduplication: {urls_before}")
        print(f"URLs After Deduplication: {urls_after}")
        print(f"Duplicate URLs Removed: {removed_urls}")
        print(f"Deduplication Rate: {(removed_urls/urls_before*100):.2f}%")
        
        # Show sample channels with URL counts
        if resources:
            print("\nSample channels:")
            sample_channels = list(resources.keys())[:5]
            for i, channel in enumerate(sample_channels, 1):
                try:
                    url_count = len(resources[channel])
                    print(f"  {i}. {channel} ({url_count} URLs)")
                except UnicodeEncodeError:
                    print(f"  {i}. [Chinese channel] ({len(resources[channel])} URLs)")

    async def run_step4_404_check(self):
        """Step4: URL可用性检测"""
        try:
            print("=" * 80)
            print(f" IPTV Resource Processing - Step4: 404 Detection")
            print("=" * 80)
            
            print("\n[Step4] Loading Step3 output and performing 404 detection...")
            
            # 读取Step3的输出文件
            step3_file = self.output_dir / "step3_unique_resources.csv"
            if not step3_file.exists():
                print(f"  Error: Step3 output file not found: {step3_file}")
                print("  Please run Step3 first using: python first.py --step3")
                return
            
            # 加载所有资源
            unique_resources = []
            try:
                with open(step3_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    
                    for row in reader:
                        if len(row) >= 2 and row[1].strip().startswith('http'):
                            resource = {
                                'name': row[0].strip(),
                                'url': row[1].strip(),
                                'category': 'Default'
                            }
                            unique_resources.append(resource)
                
                print(f"  Loaded {len(unique_resources)} unique resources from Step3")
                
            except Exception as e:
                print(f"  Error loading Step3 file: {e}")
                return
            
            # Step4: 404 Detection
            print(f"  Performing 404 detection...")
            valid_resources = await self._step4_check_404(unique_resources)
            
            print(f"  Step4 completed, valid resources: {len(valid_resources)}")
            await self._save_step4_output(valid_resources)
            await self._print_step4_summary(valid_resources, len(unique_resources))
            
        except Exception as e:
            print(f"  Error in Step4: {e}")
            import traceback
            traceback.print_exc()
    
    async def _step4_check_404(self, resources):
        """Step4: 使用异步HTTP请求检测URL可访问性（非404）"""
        if not resources:
            return []
        
        print(f"  Checking {len(resources)} URLs for 404 status...")
        print(f"  Using async HTTP requests with concurrent connections...")
        
        total = len(resources)
        if total == 0:
            return []
        
        valid_resources = []
        
        # 创建连接限制的会话
        connector = aiohttp.TCPConnector(
            limit=200,  # 总连接限制
            limit_per_host=50,  # 每主机连接限制
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )
        
        timeout = aiohttp.ClientTimeout(
            total=15,  # 总超时15秒
            connect=5,  # 连接超时5秒
            sock_read=10  # 读取超时10秒
        )
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 分批处理以避免系统过载
            batch_size = 100  # 增加批次大小
            for batch_start in range(0, total, batch_size):
                batch_end = min(batch_start + batch_size, total)
                batch = resources[batch_start:batch_end]
                
                # 为当前批次创建任务
                tasks = [self._check_url_async(session, resource.copy()) for resource in batch]
                
                # 并发执行批次
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                for result in results:
                    if isinstance(result, Exception):
                        continue
                    
                    if result.get('passed_404', False):
                        valid_resources.append(result)
                
                # 进度更新
                if batch_end % 100 == 0 or batch_end == total:
                    print(f"\r  404 detection progress: {batch_end}/{total}", end='', flush=True)
        
        print(f"\n  404 detection completed: {total} checked, {len(valid_resources)} valid")
        
        return valid_resources
    
    async def _check_url_async(self, session, resource):
        """使用异步HTTP请求检查URL是否可访问（非404）"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # 首先尝试HEAD请求（更快）
            try:
                async with session.head(resource['url'], headers=headers, allow_redirects=True) as response:
                    # 检查状态码，非404且在2xx-3xx范围内视为可访问
                    if response.status == 200:
                        resource['passed_404'] = True
                        resource['status_code'] = response.status
                        return resource
                    elif 200 <= response.status < 400:
                        # 2xx和3xx状态码都视为可访问
                        resource['passed_404'] = True
                        resource['status_code'] = response.status
                        return resource
                    else:
                        resource['passed_404'] = False
                        resource['status_code'] = response.status
                        return resource
            except Exception as head_error:
                # 如果HEAD失败，尝试GET请求
                pass
            
            # 回退到GET请求
            async with session.get(resource['url'], headers=headers, allow_redirects=True) as response:
                if response.status == 200:
                    resource['passed_404'] = True
                    resource['status_code'] = response.status
                    return resource
                elif 200 <= response.status < 400:
                    # 2xx和3xx状态码都视为可访问
                    resource['passed_404'] = True
                    resource['status_code'] = response.status
                    return resource
                else:
                    resource['passed_404'] = False
                    resource['status_code'] = response.status
                    return resource
                
        except Exception as e:
            resource['passed_404'] = False
            resource['status_code'] = 0
            resource['error'] = str(e)
            return resource
    
    async def _save_step4_output(self, resources):
        """保存Step4输出文件"""
        try:
            step4_file = self.output_dir / "step4_valid_resources.csv"
            with open(step4_file, 'w', encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['resource_name', 'url'])
                
                for resource in resources:
                    writer.writerow([resource['name'], resource['url']])
            
            print(f"  Saved file: {step4_file}")
            
            # Count valid URLs
            total_urls = len(resources)
            print(f"  Valid URLs: {total_urls}/{total_urls}")
            
        except Exception as e:
            print(f"  Error saving Step4 CSV: {e}")
    
    async def _print_step4_summary(self, resources, total_checked):
        """打印Step4完成摘要"""
        print("\n" + "="*60)
        print("Step4 404 Detection - Completion Summary")
        print("="*60)
        
        total_channels = len(set(r['name'] for r in resources))
        total_valid_urls = len(resources)
        
        print(f"Total Channels: {total_channels}")
        print(f"URLs Checked: {total_checked}")
        print(f"Valid URLs: {total_valid_urls}")
        print(f"Valid Rate: {(total_valid_urls/total_checked*100):.2f}%")
        
        # Show sample channels
        if resources:
            print("\nSample valid channels:")
            sample_channels = list(set(r['name'] for r in resources))[:5]
            for i, channel in enumerate(sample_channels, 1):
                try:
                    url_count = len([r for r in resources if r['name'] == channel])
                    print(f"  {i}. {channel} ({url_count} URLs)")
                except UnicodeEncodeError:
                    print(f"  {i}. [Chinese channel] ({len([r for r in resources if r['name'] == channel])} URLs)")

    async def run_step5_speed_test(self):
        """Step5: URL速度测试 - 使用url-check-v-pro.py风格实现"""
        try:
            print("=" * 80)
            print("IPTV Resource Processing - Step5 Speed Test (FINAL VERSION)")
            print("=" * 80)
            
            # 读取Step4的输出文件
            step4_file = self.output_dir / "step4_valid_resources.csv"
            if not step4_file.exists():
                print(f"  error: Step4 file not found: {step4_file}")
                print("  please run Step4 first: python first.py --step4")
                return
            
            print(f"\n Step5: speed testing...")
            print(f" loading Step4 results from {step4_file}...")
            
            # 加载所有有效资源
            valid_resources = []
            try:
                import csv
                with open(step4_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # skip header
                    
                    for row in reader:
                        if len(row) >= 2 and row[1].strip().startswith('http'):
                            resource = {
                                'name': row[0].strip(),
                                'url': row[1].strip(),
                                'category': 'Default'
                            }
                            valid_resources.append(resource)
                
                print(f" loaded {len(valid_resources)} valid resources from Step4")
                
            except Exception as e:
                print(f" error loading Step4 file: {e}")
                return
            
            # 使用url-check-v-pro.py风格的速度测试
            speed_resources = await self._step5_test_speed_url_check_style(valid_resources)
            
            # 保存结果
            await self._save_step5_output_url_check_style(speed_resources, len(valid_resources))
            
        except KeyboardInterrupt:
            print("\n  Step5 interrupted by user")
        except Exception as e:
            print(f"  Error in Step5: {e}")
            import traceback
            traceback.print_exc()
    
    async def _step5_test_speed_url_check_style(self, valid_resources):
        """使用url-check-v-pro.py风格的速度测试"""
        print(f" performing speed testing using url-check-v-pro.py method...")
        
        total = len(valid_resources)
        if total == 0:
            print(" no resources to test")
            return []
        
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
        from multiprocessing import Manager
        from functools import partial
        
        # 使用与url-check-v-pro.py相同的进程数
        max_workers = max(6, multiprocessing.cpu_count())
        print(f" starting {max_workers} processes for speed testing...")
        
        manager = Manager()
        progress_dict = manager.dict()
        progress_dict['processed'] = 0
        progress_dict['total'] = total
        
        speed_resources = []
        
        try:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                worker_func = partial(self._test_speed_worker_url_check_style, progress_dict=progress_dict)
                
                for resource in valid_resources:
                    future = executor.submit(worker_func, resource)
                    futures.append(future)
                
                for future in futures:
                    try:
                        res = future.result(timeout=1800)  # 30 minutes timeout
                        speed_resources.append(res)
                    except FutureTimeoutError:
                        print(f"\n speed test timeout, forcing termination")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    except Exception as e:
                        print(f"\n individual speed test task error: {e}")
                        continue
        
        except Exception as e:
            print(f"\n speed test process pool error: {e}")
        
        # 过滤成功的速度测试，阈值 >= 0.2 MB/s
        successful_resources = [r for r in speed_resources if r.get('speed', -1) > 0]
        threshold_resources = [r for r in successful_resources if r.get('speed', -1) >= 0.2]
        
        print(f"\n speed test completed: {total} tested, {len(successful_resources)} successful")
        print(f" speed threshold >= 0.2 MB/s: {len(threshold_resources)} resources pass")
        
        return threshold_resources
    
    def _test_speed_worker_url_check_style(self, resource, progress_dict):
        """url-check-v-pro.py风格的速度测试工作进程"""
        try:
            # 解析流URL
            stream_urls = []
            url = resource.get('url', '')
            
            if url.lower().endswith(('.flv', '.mp4', '.ts', '.mkv', '.avi', '.mov')):
                stream_urls.append(url)
            else:
                stream_urls = self._get_stream_url(url)
            
            if not stream_urls:
                raise Exception('failed to parse valid stream URL')
            
            # 测试第一个流URL
            downloader = self._Downloader(stream_urls[0])
            self._download_tester(downloader)
            speed = downloader.getSpeed()
            
            # 转换为MB/s和KB/s
            if speed > 0:
                speed_mb = speed / (1024 * 1024)
                speed_kb = speed / 1024
            else:
                speed_mb = -1
                speed_kb = -1
            
            # 存储所有速度值
            resource['speed'] = speed_mb  # 主要速度（MB/s）
            resource['speed_kb'] = speed_kb
            resource['speed_bytes'] = speed
            resource['downloaded'] = downloader.recive
            
        except Exception as e:
            resource['speed'] = -1
            resource['speed_kb'] = -1
            resource['speed_bytes'] = -1
            resource['downloaded'] = 0
            resource['error'] = str(e)
        
        progress_dict['processed'] += 1
        processed = progress_dict['processed']
        total = progress_dict['total']
        if processed % 10 == 0:
            print(f"\r speed test progress: {processed}/{total}", end='', flush=True)
        
        return resource
    
    class _Downloader:
        """url-check-v-pro.py风格的下载器类"""
        def __init__(self, url):
            self.url = url
            self.startTime = time.time()
            self.recive = 0
            self.endTime = None
        
        def getSpeed(self):
            """计算速度（字节/秒）"""
            if self.endTime and self.recive != -1 and (self.endTime - self.startTime) > 0:
                return self.recive / (self.endTime - self.startTime)
            else:
                return -1
    
    def _get_stream_url(self, m3u8, depth=1):
        """解析M3U8流URL - url-check-v-pro.py风格"""
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError, URLError
        
        MAX_RECURSION_DEPTH = 2
        urls = []
        
        if depth > MAX_RECURSION_DEPTH:
            return urls
        
        try:
            req = Request(m3u8, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=5) as resp:
                prefix = ''
                if '/' in m3u8:
                    prefix = m3u8[:m3u8.rindex('/') + 1]
                
                firstLine = True
                top = False
                second = False
                lines_processed = 0
                max_lines = 100
                
                for line in resp:
                    lines_processed += 1
                    if lines_processed > max_lines:
                        break
                        
                    line = line.decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                    
                    if firstLine:
                        if line != '#EXTM3U':
                            urls.append(m3u8)
                            break
                        firstLine = False
                        continue
                    
                    if top:
                        if not line.lower().startswith('http'):
                            line = prefix + line
                        nested_urls = self._get_stream_url(line, depth + 1)
                        urls.extend(nested_urls)
                        top = False
                    elif second:
                        if not line.lower().startswith('http'):
                            line = prefix + line
                        urls.append(line)
                        second = False
                    elif line.startswith('#EXT-X-STREAM-INF:'):
                        top = True
                    elif line.startswith('#EXTINF:'):
                        second = True
                
                urls = list(dict.fromkeys(urls))[:3]
        
        except Exception:
            pass
        
        return urls
    
    def _download_tester(self, downloader):
        """下载速度测试器 - url-check-v-pro.py风格"""
        from urllib.request import Request, urlopen
        
        chunk_size = 10240  # 10KB块
        
        try:
            req = Request(downloader.url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=5) as resp:
                while time.time() - downloader.startTime < 3:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    downloader.recive += len(chunk)
                    if downloader.recive // chunk_size >= 10:
                        if time.time() - downloader.startTime >= 3:
                            break
        
        except Exception:
            downloader.recive = -1
        finally:
            downloader.endTime = time.time()
    
    def _resolve_m3u8_url(self, url):
        """解析M3U8流地址获取真实流URL"""
        try:
            import requests
            
            # 如果不是M3U8链接，直接返回
            if not url.lower().endswith('.m3u8') and 'm3u8' not in url.lower():
                return url
            
            # 请求M3U8文件
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return url
            
            m3u8_content = response.text
            
            # 查找最高质量的流URL
            lines = m3u8_content.split('\n')
            stream_urls = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('http'):
                        stream_urls.append(line)
                    elif line.startswith('/') or not line.startswith('#'):
                        # 相对路径
                        from urllib.parse import urljoin
                        base_url = url.rsplit('/', 1)[0]
                        stream_urls.append(urljoin(base_url, line))
            
            # 返回第一个找到的流URL（通常是最高质量的）
            if stream_urls:
                return stream_urls[0]
            
            return url
            
        except Exception:
            return url
    
    def _measure_download_speed(self, url, duration=3):
        """3秒下载测试带宽计算实际下载速度（MB/s）"""
        try:
            import requests
            import time
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            start_time = time.time()
            total_bytes = 0
            
            # 使用更短的超时时间来提高响应性
            response = requests.get(url, headers=headers, stream=True, timeout=(5, 10))  # 连接5秒，读取10秒
            
            if response.status_code != 200:
                return -1
            
            # 下载指定时间的数据
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        total_bytes += len(chunk)
                        
                        # 检查是否达到指定时间
                        if time.time() - start_time >= duration:
                            break
                        
                        # 安全检查：如果下载时间过长，强制退出
                        if time.time() - start_time >= duration + 2:
                            break
            except Exception:
                # 即使下载中断，也计算已下载的数据
                pass
            finally:
                response.close()
            
            # 计算速度（MB/s）
            elapsed_time = time.time() - start_time
            if elapsed_time > 0 and total_bytes > 0:
                speed_mbps = (total_bytes / (1024 * 1024)) / elapsed_time
                return round(speed_mbps, 2)
            
            return -1
            
        except requests.exceptions.Timeout:
            return -2  # 超时标记
        except requests.exceptions.ConnectionError:
            return -3  # 连接错误标记
        except Exception:
            return -1
    
    async def _save_step5_output(self, resources):
        """保存Step5输出文件"""
        try:
            step5_file = self.output_dir / "step5_speed_resources.csv"
            with open(step5_file, 'w', encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['resource_name', 'url', 'speed', 'has_video', 'has_audio'])
                
                for resource in resources:
                    writer.writerow([
                        resource['name'],
                        resource['url'],
                        resource.get('speed', -1),
                        resource.get('has_video', False),
                        resource.get('has_audio', False)
                    ])
            
            print(f"  Saved file: {step5_file}")
            
            # Count valid URLs
            total_urls = len(resources)
            print(f"  Valid URLs: {total_urls}/{total_urls}")
            
        except Exception as e:
            print(f"  Error saving Step5 CSV: {e}")
    
    async def _save_step5_output_url_check_style(self, threshold_resources, total_valid):
        """保存Step5输出文件 - url-check-v-pro.py风格"""
        import csv
        from pathlib import Path
        
        # 确保输出目录存在
        Path("output").mkdir(exist_ok=True)
        
        try:
            output_file = "output/step5_speed_resources.csv"
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['resource_name', 'url', 'speed_mb'])
                
                for resource in threshold_resources:
                    speed_value = resource.get('speed', -1)
                    if speed_value > 0:
                        speed_formatted = f"{speed_value:.5f}"
                    else:
                        speed_formatted = "-1"
                    
                    writer.writerow([
                        resource.get('name', ''),
                        resource.get('url', ''),
                        speed_formatted
                    ])
            
            print(f" saved file: {output_file}")
            print(f" saved {len(threshold_resources)} resources with speed >= 0.2 MB/s")
            
            # 验证文件是否创建
            if Path(output_file).exists():
                file_size = Path(output_file).stat().st_size
                print(f" file size: {file_size:,} bytes")
            else:
                print(f" warning: file was not created properly")
            
            # 统计信息
            if threshold_resources:
                avg_speed_mb = sum(r.get('speed', 0) for r in threshold_resources if r.get('speed', 0) > 0) / len(threshold_resources)
                max_speed_mb = max(r.get('speed', 0) for r in threshold_resources)
                
                print("\n" + "=" * 60)
                print("Step5 speed test completed - summary (FINAL VERSION)")
                print("=" * 60)
                print(f"average speed: {avg_speed_mb:.5f} MB/s")
                print(f"max speed: {max_speed_mb:.5f} MB/s")
                print(f"threshold pass rate: {len(threshold_resources)}/{total_valid} ({len(threshold_resources)/total_valid*100:.1f}%)")
                print(f"resources >= 0.2 MB/s: {len(threshold_resources)}")
                print("=" * 60)
        
        except Exception as e:
            print(f" error saving file: {e}")
            import traceback
            traceback.print_exc()
    
    async def _print_step5_summary(self, resources, total_valid):
        """打印Step5完成摘要"""
        print("\n" + "="*60)
        print("Step5 Speed Testing - Completion Summary")
        print("="*60)
        
        total_channels = len(set(r['name'] for r in resources))
        total_tested_urls = len(resources)
        
        print(f"Total Channels: {total_channels}")
        print(f"URLs Tested: {total_valid}")
        print(f"Speed Tested URLs: {total_tested_urls}")
        
        if resources:
            # 计算速度统计
            speed_values = [r.get('speed', 0) for r in resources if r.get('speed', 0) > 0]
            if speed_values:
                avg_speed = sum(speed_values) / len(speed_values)
                max_speed = max(speed_values)
                
                print(f"Average Speed: {avg_speed:.2f} MB/s")
                print(f"Max Speed: {max_speed:.2f} MB/s")
                print(f"Success Rate: {total_tested_urls}/{total_valid} ({total_tested_urls/total_valid*100:.1f}%)")
            else:
                print("No successful speed tests")
        
        # Show sample channels with speed info
        if resources:
            print("\nSample channels with speed:")
            sample_channels = list(set(r['name'] for r in resources))[:5]
            for i, channel in enumerate(sample_channels, 1):
                try:
                    channel_resources = [r for r in resources if r['name'] == channel]
                    if channel_resources:
                        avg_speed = sum(r.get('speed', 0) for r in channel_resources if r.get('speed', 0) > 0) / len([r for r in channel_resources if r.get('speed', 0) > 0]) if any(r.get('speed', 0) > 0 for r in channel_resources) else 0
                        url_count = len(channel_resources)
                        print(f"  {i}. {channel} ({url_count} URLs, Avg Speed: {avg_speed:.2f} MB/s)")
                    else:
                        print(f"  {i}. {channel} (0 URLs)")
                except UnicodeEncodeError:
                    print(f"  {i}. [Chinese channel]")

    def _format_duration(self, seconds):
        """ Format duration in human readable format """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    async def run_complete_pipeline(self):
        """执行完整的IPTV资源处理流程：Step1 → Step2 → Step3 → Step4 → Step5"""
        try:
            main_start_time = time.time()
            
            print("=" * 80)
            print(f" IPTV Resource Processing - Complete Pipeline")
            print("=" * 80)
            
            # Step1: 资源加载
            print("\n" + "="*60)
            print("STEP 1: Resource Loading (No Deduplication)")
            print("="*60)
            await self.run_step1_only()
            
            # Step2: 去黑名单和去注释
            print("\n" + "="*60)
            print("STEP 2: De-black & De-annotation")
            print("="*60)
            await self.run_step2_deblack_deannotation()
            
            # Step3: URL去重
            print("\n" + "="*60)
            print("STEP 3: URL Deduplication")
            print("="*60)
            await self.run_step3_deduplicate()
            
            # Step4: 404检测
            print("\n" + "="*60)
            print("STEP 4: 404 Detection")
            print("="*60)
            await self.run_step4_404_check()
            
            # Step5: 速度测试
            print("\n" + "="*60)
            print("STEP 5: Speed Testing")
            print("="*60)
            await self.run_step5_speed_test()
            
            # 完成摘要
            total_time = time.time() - main_start_time
            print("\n" + "="*80)
            print(" COMPLETE PIPELINE - FINAL SUMMARY")
            print("="*80)
            print(f"Total processing time: {self._format_duration(total_time)}")
            print("All steps completed successfully!")
            print("="*80)
            
        except Exception as e:
            print(f"  Error in complete pipeline: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """ Main function - Step1, Step3, Step4, and Step5 """
    import sys
    
    processor = IPTVResourceProcessor()
    
    # Check arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--step1":
            await processor.run_step1_only()
        elif sys.argv[1] == "--step2":
            await processor.run_step2_deblack_deannotation()
        elif sys.argv[1] == "--step3":
            await processor.run_step3_deduplicate()
        elif sys.argv[1] == "--step4":
            await processor.run_step4_404_check()
        elif sys.argv[1] == "--step5":
            await processor.run_step5_speed_test()
        elif sys.argv[1] == "--all":
            await processor.run_complete_pipeline()
        else:
            print("Usage:")
            print("  python first.py --step1    # Run Step1: Resource loading (no deduplication)")
            print("  python first.py --step2    # Run Step2: De-black & De-annotation")
            print("  python first.py --step3    # Run Step3: URL deduplication")
            print("  python first.py --step4    # Run Step4: 404 detection")
            print("  python first.py --step5    # Run Step5: Speed testing")
            print("  python first.py --all      # Run complete pipeline: Step1 → Step2 → Step3 → Step4 → Step5")
            print("\nNote: Steps must be run in order: Step1 -> Step2 -> Step3 -> Step4 -> Step5")
    else:
        print("Usage:")
        print("  python first.py --step1    # Run Step1: Resource loading (no deduplication)")
        print("  python first.py --step2    # Run Step2: De-black & De-annotation")
        print("  python first.py --step3    # Run Step3: URL deduplication")
        print("  python first.py --step4    # Run Step4: 404 detection")
        print("  python first.py --step5    # Run Step5: Speed testing")
        print("  python first.py --all      # Run complete pipeline: Step1 → Step2 → Step3 → Step4 → Step5")
        print("\nNote: Steps must be run in order: Step1 -> Step2 -> Step3 -> Step4 -> Step5")
        print("Running complete pipeline by default...")
        await processor.run_complete_pipeline()

if __name__ == "__main__":
    asyncio.run(main())
