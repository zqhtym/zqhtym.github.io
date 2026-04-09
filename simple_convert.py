#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple M3U converter for GitHub Actions
"""

import os
import sys

def simple_convert(txt_file, m3u_file):
    """Simple conversion function"""
    try:
        print(f"Converting {txt_file} to {m3u_file}")
        
        # Check if input file exists
        if not os.path.exists(txt_file):
            print(f"ERROR: Input file {txt_file} not found")
            return False
        
        # Read input file
        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"Read {len(lines)} lines from {txt_file}")
        
        # Write M3U file
        with open(m3u_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            
            for line in lines:
                line = line.strip()
                if line and ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        url = parts[1].strip()
                        if url.startswith('http'):
                            f.write(f"#EXTINF:-1,{name}\n")
                            f.write(f"{url}\n")
        
        print(f"Successfully converted {txt_file} to {m3u_file}")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        txt_file = sys.argv[1]
        m3u_file = sys.argv[2]
        success = simple_convert(txt_file, m3u_file)
        sys.exit(0 if success else 1)
    else:
        print("Usage: python simple_convert.py <input.txt> <output.m3u>")
        sys.exit(1)
