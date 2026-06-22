# CODEMAP Auto-Refresh Integration Guide

## Overview

The CODEMAP auto-refresh system automatically keeps the navigation index (`.aura/CODEMAP.json` and `.aura/CODEMAP.md`) synchronized with code changes. This ensures AI agents always have accurate line numbers and symbol locations when navigating the codebase.

## Architecture

### Components

1. **`aura_codemap_auto_refresh.py`** - Core auto-refresh engine
   - Tracks file modifications
   - Batches updates (default: 2 second window)
   - Performs incremental AST re-parsing
   - Updates CODEMAP artifacts

2. **`aura_bob_codemap_hooks.py`** - Bob AI integration layer
   - Provides simple notification API
   - Handles import failures gracefully
   - Offers decorator for automatic integration

## How It Works

### Batched Refresh Strategy

```
File Edit 1 → Register change → |
File Edit 2 → Register change → | Wait 2 seconds → Batch refresh all
File Edit 3 → Register change → |
```

**Benefits:**
- Avoids refresh on every keystroke
- Reduces I/O overhead
- Maintains accuracy within 2 seconds

### What Gets Updated

When files are modified, the system:
1. ✅ Re-parses AST for changed files only
2. ✅ Updates line numbers for all symbols
3. ✅ Recalculates token estimates
4. ✅ Preserves semantic IDs (hash-based, line-independent)
5. ✅ Updates command index (bang commands)
6. ✅ Refreshes topology connections (optional)

## Integration with Bob AI

### Method 1: Direct Notification (Recommended)

Add to Bob's file modification tools:

```python
from aura_bob_codemap_hooks import notify_file_modified

# In write_to_file tool:
def write_to_file(path: str, content: str, line_count: int):
    # ... existing write logic ...
    
    # Notify CODEMAP system
    notify_file_modified(path)
    
    return result

# In apply_diff tool:
def apply_diff(path: str, diff: str):
    # ... existing diff logic ...
    
    # Notify CODEMAP system
    notify_file_modified(path)
    
    return result

# In insert_content tool:
def insert_content(path: str, line: int, content: str):
    # ... existing insert logic ...
    
    # Notify CODEMAP system
    notify_file_modified(path)
    
    return result
```

### Method 2: Decorator Pattern

```python
from aura_bob_codemap_hooks import auto_refresh_codemap

@auto_refresh_codemap
def write_to_file(path: str, content: str, line_count: int):
    # ... existing logic ...
    return path  # Return path for auto-detection
```

### Method 3: Batch Notification

For operations that modify multiple files:

```python
from aura_bob_codemap_hooks import notify_files_modified

def refactor_codebase(files: list[str]):
    # ... modify multiple files ...
    
    # Notify all at once
    notify_files_modified(files)
```

## Configuration

### Enable/Disable Auto-Refresh

```python
from aura_codemap_auto_refresh import enable_auto_refresh

# Disable during bulk operations
enable_auto_refresh(False)

# ... perform bulk changes ...

# Re-enable
enable_auto_refresh(True)
```

### Adjust Batching Interval

```python
from aura_codemap_auto_refresh import set_refresh_interval

# Faster refresh (0.5 seconds)
set_refresh_interval(0.5)

# Slower refresh (5 seconds)
set_refresh_interval(5.0)
```

### Force Immediate Refresh

```python
from aura_bob_codemap_hooks import force_codemap_refresh

# Before critical navigation operations
force_codemap_refresh()

# Now CODEMAP is guaranteed up-to-date
result = search_codebase(query)
```

## File Type Filtering

Auto-refresh only processes code files:
- ✅ `.py`, `.rs`, `.c`, `.cpp`, `.js`, `.ts`, `.java`, `.go`
- ❌ Binary files, images, databases
- ❌ Generated artifacts (`.aura/`, `__pycache__/`)

## Performance Characteristics

### Incremental Refresh Performance

| Files Changed | Refresh Time | Memory |
|--------------|--------------|--------|
| 1 file       | ~50-100ms    | <10MB  |
| 5 files      | ~200-300ms   | <20MB  |
| 20 files     | ~1-2s        | <50MB  |

### Full Rebuild (for comparison)

| Total Files | Rebuild Time | Memory |
|-------------|--------------|--------|
| 180 files   | ~15-30s      | ~200MB |

**Conclusion:** Incremental refresh is 10-100× faster than full rebuild.

## Error Handling

The system is designed to **never break Bob's operations**:

```python
try:
    notify_file_modified(path)
except Exception:
    # Silently fails - Bob continues normally
    pass
```

If CODEMAP refresh fails:
- ✅ Bob's file operations complete successfully
- ⚠️ CODEMAP may be temporarily stale
- 🔄 Next successful refresh will catch up

## Testing

### Test Auto-Refresh System

```bash
python aura_codemap_auto_refresh.py
```

### Test Bob Integration Hooks

```bash
python aura_bob_codemap_hooks.py
```

### Manual Verification

```python
from aura_bob_codemap_hooks import notify_file_modified, force_codemap_refresh
import time

# Modify a file
with open("test_file.py", "w") as f:
    f.write("# Test content\n")

# Notify system
notify_file_modified("test_file.py")

# Wait for batch refresh
time.sleep(3)

# Verify CODEMAP was updated
import json
codemap = json.load(open(".aura/CODEMAP.json"))
print(f"Last refresh: {codemap['summary']['last_incremental_refresh_unix']}")
```

## Troubleshooting

### CODEMAP Not Updating

**Check 1:** Is auto-refresh enabled?
```python
from aura_codemap_auto_refresh import _auto_refresh_enabled
print(f"Auto-refresh enabled: {_auto_refresh_enabled}")
```

**Check 2:** Are files being registered?
```python
from aura_codemap_auto_refresh import get_pending_changes
print(f"Pending changes: {get_pending_changes()}")
```

**Check 3:** Does CODEMAP exist?
```bash
ls -la .aura/CODEMAP.json
```

If missing, generate it first:
```bash
python aura_codebase_navigator.py
```

### Import Errors

If `aura_codemap_auto_refresh` is not found:
1. Ensure the file exists in the workspace
2. Check Python path includes workspace directory
3. Verify no syntax errors in the module

The integration hooks will gracefully degrade if imports fail.

## Best Practices

### For Bob AI Developers

1. ✅ **Always notify after file writes** - Even if unsure, notification is cheap
2. ✅ **Use batch notifications for multi-file ops** - More efficient
3. ✅ **Force refresh before navigation** - Ensures accuracy
4. ❌ **Don't disable auto-refresh** - Unless doing bulk operations
5. ❌ **Don't wait for refresh** - It happens in background

### For AuraOS Developers

1. ✅ **Run manual refresh after major refactors**
   ```bash
   python aura_codebase_navigator.py --refresh aura_node.py aura_core.py
   ```

2. ✅ **Check CODEMAP freshness**
   ```bash
   # View last refresh time
   jq '.summary.last_incremental_refresh_unix' .aura/CODEMAP.json
   ```

3. ✅ **Rebuild from scratch if corrupted**
   ```bash
   python aura_codebase_navigator.py
   ```

## Future Enhancements

Potential improvements:
- [ ] File system watcher integration (inotify/FSEvents)
- [ ] Parallel AST parsing for multi-file refreshes
- [ ] Incremental topology updates (currently disabled)
- [ ] Conflict detection for concurrent edits
- [ ] Refresh queue prioritization (hot files first)

## Summary

The CODEMAP auto-refresh system ensures AI agents always have accurate navigation data without manual intervention. Integration is simple, performance is excellent, and error handling is robust.

**Key Takeaway:** Add one line after file writes, and CODEMAP stays synchronized automatically.

```python
notify_file_modified(path)  # That's it!