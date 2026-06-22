#!/usr/bin/env python3
"""
Simple test for CODEMAP auto-refresh integration hooks.
This test doesn't require numpy or other heavy dependencies.
"""

import sys
import time
from pathlib import Path

def test_integration_hooks():
    """Test the Bob integration hooks in isolation."""
    print("=" * 60)
    print("CODEMAP Integration Hooks Test")
    print("=" * 60)
    
    # Test 1: Import integration hooks
    print("\n[Test 1] Importing integration hooks...")
    try:
        from aura_bob_codemap_hooks import (
            notify_file_modified,
            notify_files_modified,
            force_codemap_refresh,
            _CODEMAP_AVAILABLE,
        )
        print("[PASS] Integration hooks imported successfully")
        print(f"       CODEMAP available: {_CODEMAP_AVAILABLE}")
    except ImportError as e:
        print(f"[FAIL] Failed to import integration hooks: {e}")
        return False
    
    # Test 2: Test notification with valid path
    print("\n[Test 2] Testing notify_file_modified()...")
    try:
        notify_file_modified("test_file.py")
        print("[PASS] notify_file_modified() executed without error")
    except Exception as e:
        print(f"[FAIL] notify_file_modified() raised exception: {e}")
        return False
    
    # Test 3: Test batch notification
    print("\n[Test 3] Testing notify_files_modified()...")
    try:
        notify_files_modified(["file1.py", "file2.py", "file3.py"])
        print("[PASS] notify_files_modified() executed without error")
    except Exception as e:
        print(f"[FAIL] notify_files_modified() raised exception: {e}")
        return False
    
    # Test 4: Test force refresh
    print("\n[Test 4] Testing force_codemap_refresh()...")
    try:
        force_codemap_refresh()
        print("[PASS] force_codemap_refresh() executed without error")
    except Exception as e:
        print(f"[FAIL] force_codemap_refresh() raised exception: {e}")
        return False
    
    # Test 5: Test error handling with invalid inputs
    print("\n[Test 5] Testing error handling...")
    try:
        # These should not raise exceptions
        notify_file_modified("/nonexistent/path.py")
        notify_file_modified(Path("/another/nonexistent.py"))
        notify_files_modified([])
        print("[PASS] Error handling works correctly")
    except Exception as e:
        print(f"[FAIL] Unexpected exception: {e}")
        return False
    
    # Test 6: Check CODEMAP status
    print("\n[Test 6] Checking CODEMAP status...")
    codemap_path = Path(".aura/CODEMAP.json")
    if codemap_path.exists():
        print(f"[INFO] CODEMAP exists at {codemap_path}")
        print("       Auto-refresh will work when dependencies are available")
    else:
        print(f"[INFO] CODEMAP not found at {codemap_path}")
        print("       Run: python aura_codebase_navigator.py")
    
    return True


def test_decorator():
    """Test the decorator functionality."""
    print("\n[Test 7] Testing decorator...")
    
    try:
        from aura_bob_codemap_hooks import auto_refresh_codemap
        
        @auto_refresh_codemap
        def mock_write_file(path: str, content: str):
            """Mock file write function."""
            return path
        
        # Call the decorated function
        result = mock_write_file("test.py", "content")
        
        if result == "test.py":
            print("[PASS] Decorator works correctly")
            return True
        else:
            print(f"[FAIL] Decorator returned unexpected value: {result}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Decorator test failed: {e}")
        return False


if __name__ == "__main__":
    print("\nTesting CODEMAP auto-refresh integration...")
    print("This test verifies the integration hooks work correctly.\n")
    
    success = True
    
    try:
        success = test_integration_hooks()
        if success:
            success = test_decorator()
    except Exception as e:
        print(f"\n[FAIL] Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("[PASS] ALL TESTS PASSED")
        print("\nIntegration hooks are ready for use!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Generate CODEMAP: python aura_codebase_navigator.py")
        print("3. Integrate with Bob's file modification tools")
    else:
        print("[FAIL] SOME TESTS FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

# Made with Bob
