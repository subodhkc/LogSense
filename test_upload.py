#!/usr/bin/env python3
"""
Static test to verify file upload and parsing functionality
"""

import tempfile
import os
from analysis import parse_logs
import sys
sys.path.append('.')
from analysis import parse_logs as parse_logs_main

def test_log_parsing():
    """Test log parsing with sample data"""
    
    # Test 1: Basic log content
    sample_log = """2024-01-15 10:30:00 INFO Starting application
2024-01-15 10:30:01 ERROR Database connection failed
2024-01-15 10:30:02 WARNING Retrying connection
2024-01-15 10:30:03 INFO Connection established"""
    
    print("=== Test 1: Basic Log Parsing ===")
    events = parse_logs(sample_log, "test.log")
    print(f"Events found: {len(events)}")
    for event in events:
        print(f"  {event}")
    
    # Test 2: Different timestamp formats
    sample_log2 = """[2024-01-15T10:30:00] Application started
[2024-01-15T10:30:01] Error: Failed to load config
Jan 15 10:30:02 System ready
10:30:03 - Process completed"""
    
    print("\n=== Test 2: Different Timestamp Formats ===")
    events2 = parse_logs(sample_log2, "test2.log")
    print(f"Events found: {len(events2)}")
    for event in events2:
        print(f"  {event}")
    
    # Test 3: No timestamps
    sample_log3 = """Application starting up
Loading configuration files
Database connection established
Ready to process requests"""
    
    print("\n=== Test 3: No Timestamps ===")
    events3 = parse_logs(sample_log3, "test3.log")
    print(f"Events found: {len(events3)}")
    for event in events3:
        print(f"  {event}")
    
    # Test 4: File-based parsing (simulate what modal does)
    print("\n=== Test 4: File-based Parsing ===")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(sample_log)
        temp_path = f.name
    
    try:
        # Simulate the modal_native_gpu.py logic
        with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        events4 = parse_logs(content, os.path.basename(temp_path))
        print(f"File events found: {len(events4)}")
        for event in events4:
            print(f"  {event}")
    finally:
        os.unlink(temp_path)
    
    # Test 5: Empty content
    print("\n=== Test 5: Empty Content ===")
    events5 = parse_logs("", "empty.log")
    print(f"Empty events found: {len(events5)}")
    
    # Test 6: Binary/non-text content
    print("\n=== Test 6: Binary Content ===")
    binary_content = b'\x00\x01\x02\x03\x04'
    events6 = parse_logs(binary_content, "binary.log")
    print(f"Binary events found: {len(events6)}")

def test_common_log_formats():
    """Test parsing common log formats"""
    
    formats = {
        "Apache": '127.0.0.1 - - [25/Dec/2024:10:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234',
        "Nginx": '2024/12/25 10:00:00 [error] 1234#0: *1 connect() failed (111: Connection refused)',
        "Syslog": 'Dec 25 10:00:00 hostname process[1234]: This is a log message',
        "Windows Event": '2024-12-25 10:00:00.123 [INFO] Application started successfully',
        "Java": '2024-12-25 10:00:00,123 INFO [main] com.example.App - Application started',
        "Python": '2024-12-25 10:00:00,123 - INFO - root - Application started'
    }
    
    print("\n=== Testing Common Log Formats ===")
    for format_name, log_line in formats.items():
        events = parse_logs(log_line, f"{format_name.lower()}.log")
        print(f"{format_name}: {len(events)} events")
        if events:
            print(f"  Sample: {events[0]}")

if __name__ == "__main__":
    print("LogSense Upload Parsing Test")
    print("=" * 40)
    
    try:
        test_log_parsing()
        test_common_log_formats()
        print("\n✅ All tests completed")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
