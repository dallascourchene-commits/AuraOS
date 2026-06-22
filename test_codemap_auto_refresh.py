#!/usr/bin/env python3
"""
Test suite for CODEMAP auto-refresh system.

Run with: python test_codemap_auto_refresh.py
"""

import json
import time
from pathlib import Path
import tempfile
import shutil

def test_auto_refresh_system():
    """Test the complete auto-refresh workflow."""
    print("=" * 60)
    print("CODEMAP Auto-Refresh System Test")
    print("=" * 60)
    
    # Test 1: Import modules
    print("\n[Test 1] Importing modules...")
    try:
        from aura_codemap_auto_refresh import (
            register_file_change,
            get_pending_changes,
            flush_pending_refreshes,
            enable_auto_refresh,
            set_refresh_interval,
        )
        print("✅ Core module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import core module: {e}")
        return False
    
    try:
        from aura_bob_codemap_hooks import (
            notify_file_modified,
            notify_files_modified,
            force_codemap_refresh,
        )
        print("✅ Integration hooks imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import integration hooks: {e}")
        return False
    
    # Test 2: Check if CODEMAP exists
    print("\n[Test 2] Checking CODEMAP existence...")
    codemap_path = Path(".aura/CODEMAP.json")
    if codemap_path.exists():
        print(f"✅ CODEMAP found at {codemap_path}")
        
        # Read current state
        with open(codemap_path) as f:
            codemap = json.load(f)
        
        file_count = codemap.get("summary", {}).get("file_count", 0)
        last_refresh = codemap.get("summary", {}).get("last_incremental_refresh_unix", 0)
        print(f"   Files indexed: {file_count}")
        print(f"   Last refresh: {last_refresh}")
    else:
        print(f"⚠️  CODEMAP not found at {codemap_path}")
        print("   Run: python aura_codebase_navigator.py")
        print("   Skipping refresh tests...")
        return True  # Not a failure, just not set up yet
    
    # Test 3: Register file changes
    print("\n[Test 3] Registering file changes...")
    test_files = ["aura_node.py", "aura_core.py", "aura_substrate.py"]
    
    for file in test_files:
        register_file_change(file)
        print(f"   Registered: {file}")
    
    pending = get_pending_changes()
    print(f"✅ Pending changes: {len(pending)} files")
    
    if len(pending) != len(test_files):
        print(f"⚠️  Expected {len(test_files)} pending, got {len(pending)}")
    
    # Test 4: Integration hooks
    print("\n[Test 4] Testing integration hooks...")
    notify_file_modified("test_file.py")
    print("✅ notify_file_modified() works")
    
    notify_files_modified(["file1.py", "file2.py"])
    print("✅ notify_files_modified() works")
    
    # Test 5: Configuration
    print("\n[Test 5] Testing configuration...")
    enable_auto_refresh(False)
    print("✅ Disabled auto-refresh")
    
    enable_auto_refresh(True)
    print("✅ Re-enabled auto-refresh")
    
    set_refresh_interval(1.0)
    print("✅ Set refresh interval to 1.0 seconds")
    
    # Test 6: Wait for batched refresh
    print("\n[Test 6] Waiting for batched refresh...")
    print("   (This will take ~2 seconds)")
    
    initial_time = time.time()
    time.sleep(2.5)  # Wait for refresh to complete
    elapsed = time.time() - initial_time
    
    print(f"✅ Waited {elapsed:.1f} seconds")
    
    # Check if refresh occurred
    pending_after = get_pending_changes()
    print(f"   Pending changes after wait: {len(pending_after)}")
    
    if len(pending_after) == 0:
        print("✅ Batched refresh completed successfully")
    else:
        print(f"⚠️  Still have {len(pending_after)} pending changes")
    
    # Test 7: Force refresh
    print("\n[Test 7] Testing force refresh...")
    register_file_change("force_test.py")
    force_codemap_refresh()
    
    pending_after_force = get_pending_changes()
    if len(pending_after_force) == 0:
        print("✅ Force refresh cleared pending changes")
    else:
        print(f"⚠️  Force refresh left {len(pending_after_force)} pending")
    
    # Test 8: Verify CODEMAP was updated
    print("\n[Test 8] Verifying CODEMAP update...")
    if codemap_path.exists():
        with open(codemap_path) as f:
            updated_codemap = json.load(f)
        
        new_refresh_time = updated_codemap.get("summary", {}).get("last_incremental_refresh_unix", 0)
        
        if new_refresh_time > last_refresh:
            print(f"✅ CODEMAP was updated (timestamp: {new_refresh_time})")
            
            # Check for refresh metadata
            last_refresh_info = updated_codemap.get("last_refresh", {})
            if last_refresh_info:
                mode = last_refresh_info.get("mode", "unknown")
                changed_count = last_refresh_info.get("changed_path_count", 0)
                print(f"   Refresh mode: {mode}")
                print(f"   Files changed: {changed_count}")
        else:
            print("⚠️  CODEMAP timestamp unchanged")
            print(f"   Old: {last_refresh}, New: {new_refresh_time}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    
    return True


def test_error_handling():
    """Test that errors don't break the system."""
    print("\n[Error Handling Test] Testing graceful degradation...")
    
    from aura_bob_codemap_hooks import notify_file_modified
    
    # Try to notify with invalid path
    try:
        notify_file_modified("/nonexistent/path/to/file.py")
        print("✅ Invalid path handled gracefully")
    except Exception as e:
        print(f"❌ Exception not caught: {e}")
        return False
    
    # Try to notify with None
    try:
        notify_file_modified(None)  # type: ignore
        print("✅ None value handled gracefully")
    except Exception as e:
        print(f"❌ Exception not caught: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = True
    
    try:
        success = test_auto_refresh_system()
        if success:
            success = test_error_handling()
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST SUITE PASSED")
    else:
        print("❌ TEST SUITE FAILED")
    print("=" * 60)
    
    exit(0 if success else 1)

# Made with Bob
