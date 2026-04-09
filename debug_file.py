#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions debug script - write to file
"""

import os
import sys

def main():
    # Create debug directory and write debug info to file
    os.makedirs('tmp', exist_ok=True)
    with open('tmp/debug.log', 'w') as f:
        f.write(f"Python version: {sys.version}\n")
        f.write(f"Current directory: {os.getcwd()}\n")
        f.write(f"Arguments: {sys.argv}\n")
        f.write(f"PYTHONOPTIMIZE: {os.environ.get('PYTHONOPTIMIZE', 'not set')}\n")
        f.write(f"Input file exists: {os.path.exists(sys.argv[1]) if len(sys.argv) > 1 else 'N/A'}\n")
        f.write(f"Input file: {sys.argv[1] if len(sys.argv) > 1 else 'N/A'}\n")
        f.write(f"Output file: {sys.argv[2] if len(sys.argv) > 2 else 'N/A'}\n")
        f.write(f"Files in current directory: {os.listdir('.')}\n")
        f.write(f"Files in parent directory: {os.listdir('..')}\n")
    
    if len(sys.argv) >= 3:
        txt_file = sys.argv[1]
        if not os.path.exists(txt_file):
            print("ERROR: Input file not found")
            sys.exit(2)
        print("SUCCESS: Test completed")
        sys.exit(0)
    else:
        print("ERROR: Not enough arguments")
        sys.exit(1)

if __name__ == "__main__":
    main()
