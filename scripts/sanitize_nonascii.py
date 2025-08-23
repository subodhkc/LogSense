#!/usr/bin/env python3
"""
Repository-wide non-ASCII character sanitization script.
Replaces common non-ASCII characters with ASCII equivalents to prevent
Windows PowerShell encoding issues across the entire codebase.
"""

import os
import sys
import re
from pathlib import Path

# Common non-ASCII to ASCII replacements
REPLACEMENTS = {
    # Em dash and en dash
    '-': '-',
    '-': '-',
    
    # Quotes
    '"': '"',
    '"': '"',
    ''''''''
    # Arrows
    '>': '>',
    'v': 'v',
    '<': '<',
    '^': '^',
    '->': '->',
    '<-': '<-',
    '^': '^',
    'v': 'v',
    
    # Bullets and symbols
    '-': '-',
    '-': '-',
    '-': '-',
    '-': '-',
    '*': '*',
    '*': '*',
    'OK': 'OK',
    'X': 'X',
    '[OK]': '[OK]',
    '[X]': '[X]',
    '[WARN]': '[WARN]',
    '[SEARCH]': '[SEARCH]',
    
    # Mathematical symbols
    'x': 'x',
    '/': '/',
    '+/-': '+/-',
    
    # Other common symbols
    '...': '...',
    ' deg': ' deg',
    '(TM)': '(TM)',
    '(C)': '(C)',
    '(R)': '(R)',
}

# Files to skip (binary files, images, etc.)
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.pdf', '.zip', '.exe', '.dll', '.so', '.dylib'}
SKIP_DIRS = {'.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules'}

def sanitize_content(content):
    """Replace non-ASCII characters with ASCII equivalents."""
    original_content = content
    
    # Apply known replacements
    for non_ascii, ascii_equiv in REPLACEMENTS.items():
        content = content.replace(non_ascii, ascii_equiv)
    
    # Handle any remaining non-ASCII characters by replacing with placeholder
    sanitized_lines = []
    for line_num, line in enumerate(content.splitlines(), 1):
        sanitized_line = ""
        for char in line:
            if ord(char) <= 127:
                sanitized_line += char
            else:
                # Replace with placeholder and note
                sanitized_line += f"[U+{ord(char):04X}]"
        sanitized_lines.append(sanitized_line)
    
    return '\n'.join(sanitized_lines), content != original_content

def should_skip_file(file_path):
    """Check if file should be skipped."""
    # Skip by extension
    if file_path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    
    # Skip by directory
    for part in file_path.parts:
        if part in SKIP_DIRS:
            return True
    
    return False

def sanitize_file(file_path, dry_run=False):
    """Sanitize a single file."""
    try:
        # Try to read as text
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        sanitized_content, changed = sanitize_content(content)
        
        if changed:
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(sanitized_content)
                return f"[FIXED] {file_path}"
            else:
                return f"[WOULD FIX] {file_path}"
        else:
            return f"[CLEAN] {file_path}"
            
    except Exception as e:
        return f"[ERROR] {file_path}: {e}"

def main():
    """Main sanitization function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sanitize non-ASCII characters in repository')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--target-dir', default='.', help='Target directory to sanitize (default: current)')
    args = parser.parse_args()
    
    root_dir = Path(args.target_dir).resolve()
    
    print(f"[SANITIZE] {'DRY RUN: ' if args.dry_run else ''}Sanitizing repository: {root_dir}")
    print("=" * 60)
    
    files_processed = 0
    files_changed = 0
    files_errors = 0
    
    # Walk through all files
    for file_path in root_dir.rglob('*'):
        if file_path.is_file() and not should_skip_file(file_path):
            result = sanitize_file(file_path, args.dry_run)
            print(result)
            
            files_processed += 1
            if '[FIXED]' in result or '[WOULD FIX]' in result:
                files_changed += 1
            elif '[ERROR]' in result:
                files_errors += 1
    
    print("=" * 60)
    print(f"[SUMMARY] Processed: {files_processed}, Changed: {files_changed}, Errors: {files_errors}")
    
    if args.dry_run and files_changed > 0:
        print(f"[INFO] Run without --dry-run to apply {files_changed} changes")

if __name__ == "__main__":
    main()