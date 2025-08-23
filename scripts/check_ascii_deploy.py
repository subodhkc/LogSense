#!/usr/bin/env python3
"""
Pre-deploy ASCII-only check script for Windows PowerShell compatibility.
Scans critical deployment files for non-ASCII characters that could cause
encoding errors during Modal CLI deployments on Windows.
"""

import os
import sys
import re
from pathlib import Path

# Critical files that are part of the deployment path
DEPLOY_CRITICAL_FILES = [
    "modal_economic.py",
    "modal_native.py", 
    "modal_native_complete.py",
    "modal_native_fixed.py",
    "templates/index.html",
    "static/app.js",
    "static/styles.css"
]

def check_file_ascii(file_path):
    """Check if a file contains only ASCII characters."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find non-ASCII characters
        non_ascii_chars = []
        for line_num, line in enumerate(content.splitlines(), 1):
            for char_pos, char in enumerate(line):
                if ord(char) > 127:
                    non_ascii_chars.append({
                        'line': line_num,
                        'pos': char_pos + 1,
                        'char': char,
                        'ord': ord(char),
                        'context': line.strip()[:50] + ('...' if len(line.strip()) > 50 else '')
                    })
        
        return non_ascii_chars
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def main():
    """Main function to check all critical deployment files."""
    root_dir = Path(__file__).parent.parent
    issues_found = False
    
    print("[CHECK] Checking deployment-critical files for non-ASCII characters...")
    print("=" * 60)
    
    for file_path in DEPLOY_CRITICAL_FILES:
        full_path = root_dir / file_path
        
        if not full_path.exists():
            print(f"[WARN] File not found: {file_path}")
            continue
            
        print(f"Checking: {file_path}")
        non_ascii = check_file_ascii(full_path)
        
        if non_ascii is None:
            print(f"[ERROR] Error reading file: {file_path}")
            issues_found = True
            continue
            
        if non_ascii:
            print(f"[FAIL] Non-ASCII characters found in {file_path}:")
            for issue in non_ascii:
                print(f"   Line {issue['line']}, Pos {issue['pos']}: '{issue['char']}' (U+{issue['ord']:04X})")
                print(f"   Context: {issue['context']}")
            issues_found = True
        else:
            print(f"[PASS] ASCII-only: {file_path}")
    
    print("=" * 60)
    
    if issues_found:
        print("[BLOCKED] DEPLOYMENT BLOCKED: Non-ASCII characters found in critical files!")
        print("   These characters can cause Windows PowerShell encoding errors.")
        print("   Please replace them with ASCII equivalents before deploying.")
        sys.exit(1)
    else:
        print("[SUCCESS] ALL CLEAR: All deployment-critical files are ASCII-only!")
        print("   Safe to deploy via Windows PowerShell CLI.")
        sys.exit(0)

if __name__ == "__main__":
    main()
