#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions debug test script
"""

import os
import sys

def main():
    print(f"DEBUG: Python version: {sys.version}")
    print(f"DEBUG: Current directory: {os.getcwd()}")
    print(f"DEBUG: Arguments: {sys.argv}")
    print(f"DEBUG: Environment PYTHONOPTIMIZE: {os.environ.get('PYTHONOPTIMIZE', 'not set')}")
    
    if len(sys.argv) >= 3:
        txt_file = sys.argv[1]
        m3u_file = sys.argv[2]
        print(f"DEBUG: Input file: {txt_file}")
        print(f"DEBUG: Output file: {m3u_file}")
        print(f"DEBUG: Input file exists: {os.path.exists(txt_file)}")
        
        if not os.path.exists(txt_file):
            print(f"ERROR: Input file not found: {txt_file}")
            sys.exit(2)
            
        print("SUCCESS: Test completed")
        sys.exit(0)
    else:
        print("ERROR: Not enough arguments")
        sys.exit(1)

if __name__ == "__main__":
    main()
