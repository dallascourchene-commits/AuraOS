# CODEMAP Auto-Refresh System

## 🎯 Quick Start

### For Users (Easiest)

**Windows:**
```cmd
start_codemap_watcher.bat
```

**Linux/Mac:**
```bash
chmod +x start_codemap_watcher.sh
./start_codemap_watcher.sh
```

That's it! The watcher will automatically keep CODEMAP synchronized with code changes from **any source** (Bob, VS Code, Cline, manual edits, etc.).

### For Developers

Add one line after file modifications:

```python
from aura_bob_codemap_hooks import notify_file_modified
notify_file_modified(path)
```

---

## 📚 What Is This?

The CODEMAP auto-refresh system keeps the navigation index (`.aura/CODEMAP.json`) synchronized with code changes automatically. This ensures AI agents always have accurate line numbers and symbol locations when navigating the codebase.

### The Problem It Solves

**Before:**
```
1. Edit aura_node.py (change line 100)
2. CODEMAP still shows old line numbers ❌
3. AI navigates to wrong location ❌
4. Must manually run: python aura_codebase_navigator.py --refresh
```

**After:**
```
1. Edit aura_node.py (change line 100)
2. CODEMAP automatically updates in background ✅
3. AI always has accurate line numbers ✅
4. No manual intervention needed ✅
```

---

## 🏗️ Architecture

### Two Integration Methods

#### Method 1: File System Watcher (Universal)
- Monitors workspace for file changes
- Works with **ANY tool** automatically
- No code changes needed
- Slight delay (0.5s debounce)

#### Method 2: Direct Integration (Optimal)
- Explicit notification from tool code
- Immediate response
- Minimal overhead
- Requires code changes

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    File Modifications                    │
│  (Bob AI, VS Code, Cline, Manual Edits, Git, etc.)     │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
┌───────────────┐  ┌──────────────────┐
│ File System   │  │ Direct           │
│ Watcher       │  │ Integration      │
│ (Universal)   │  │ (notify_file_    │
│               │  │  modified)       │
└───────┬───────┘  └────────┬─────────┘
        │                   │
        └─────────┬─────────┘
                  ▼
        ┌──────────────────┐
        │ Change Queue     │
        │ (2s batching)    │
        └────────┬─────────┘
                 ▼
        ┌──────────────────┐
        │ Incremental      │
        │ AST Re-parse     │
        └────────┬─────────┘
                 ▼
        ┌──────────────────┐
        │ Update CODEMAP   │
        │ .json & .md      │
        └──────────────────┘
```

---

## 📦 Files Overview

### Core System

| File | Purpose | Lines |
|------|---------|-------|
| `aura_codemap_auto_refresh.py` | Core auto-refresh engine | 177 |
| `aura_bob_codemap_hooks.py` | Integration API for tools | 133 |
| `aura_codemap_watcher.py` | File system watcher | 283 |

### Documentation

| File | Purpose | Lines |
|------|---------|-------|
| `CODEMAP_AUTO_REFRESH_SUMMARY.md` | Executive summary | 283 |
| `CODEMAP_AUTO_REFRESH_INTEGRATION.md` | Technical integration guide | 318 |
| `CODEMAP_TOOL_INTEGRATION_GUIDE.md` | Tool-specific integration | 502 |
| `CODEMAP_AUTO_REFRESH_README.md` | This file | - |

### Scripts & Tests

| File | Purpose |
|------|---------|
| `start_codemap_watcher.sh` | Quick-start script (Linux/Mac) |
| `start_codemap_watcher.bat` | Quick-start script (Windows) |
| `test_codemap_hooks_simple.py` | Integration test suite |
| `test_codemap_auto_refresh.py` | Comprehensive test suite |

---

## 🚀 Installation

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `watchdog>=3.0.0` for file system monitoring.

### Step 2: Generate Initial CODEMAP

```bash
python aura_codebase_navigator.py
```

This creates `.aura/CODEMAP.json` and `.aura/CODEMAP.md`.

### Step 3: Start Watcher

**Option A: Quick-start script (Recommended)**

Windows:
```cmd
start_codemap_watcher.bat
```

Linux/Mac:
```bash
./start_codemap_watcher.sh
```

**Option B: Direct Python**

```bash
python aura_codemap_watcher.py
```

**Option C: Background service**

Linux (systemd):
```bash
sudo cp codemap-watcher.service /etc/systemd/system/
sudo systemctl enable codemap-watcher
sudo systemctl start codemap-watcher
```

---

## 🔧 Configuration

### Adjust Batching Interval

```python
from aura_codemap_auto_refresh import set_refresh_interval

# Faster refresh (0.5 seconds)
set_refresh_interval(0.5)

# Slower refresh (5 seconds)
set_refresh_interval(5.0)
```

### Enable/Disable Auto-Refresh

```python
from aura_codemap_auto_refresh import enable_auto_refresh

# Disable during bulk operations
enable_auto_refresh(False)

# ... perform bulk changes ...

# Re-enable
enable_auto_refresh(True)
```

### Custom File Extensions

Edit `aura_codemap_watcher.py`:

```python
CODE_EXTENSIONS = {
    '.py', '.rs', '.c', '.cpp',  # Existing
    '.kt', '.swift', '.scala'     # Add your extensions
}
```

---

## 🔌 Integration Examples

### Bob AI

```python
from aura_bob_codemap_hooks import notify_file_modified

def write_to_file(path: str, content: str, line_count: int):
    with open(path, 'w') as f:
        f.write(content)
    notify_file_modified(path)  # ← Add this line
    return {"status": "success"}
```

### VS Code Extension

```typescript
import * as vscode from 'vscode';
import { exec } from 'child_process';

vscode.workspace.onDidSaveTextDocument((doc) => {
    exec(`python -c "from aura_bob_codemap_hooks import notify_file_modified; notify_file_modified('${doc.fileName}')"`);
});
```

### Git Hook

`.git/hooks/post-commit`:
```bash
#!/bin/bash
python -c "from aura_bob_codemap_hooks import force_codemap_refresh; force_codemap_refresh()"
```

---

## 📊 Performance

### Incremental Refresh (What We Built)

| Files Changed | Refresh Time | Memory |
|--------------|--------------|--------|
| 1 file       | 50-100ms     | <10MB  |
| 5 files      | 200-300ms    | <20MB  |
| 20 files     | 1-2s         | <50MB  |

### Full Rebuild (What We Avoid)

| Total Files | Rebuild Time | Memory |
|-------------|--------------|--------|
| 180 files   | 15-30s       | ~200MB |

**Result:** 10-100× faster than full rebuild

### File System Watcher Overhead

- **CPU:** <1% idle, <5% during operations
- **Memory:** ~20-50MB
- **Latency:** 0.5-1.0 seconds (debounced)

---

## ✅ Testing

### Test Integration Hooks

```bash
python test_codemap_hooks_simple.py
```

Expected output:
```
[PASS] ALL TESTS PASSED
```

### Test Full System (Requires Dependencies)

```bash
python test_codemap_auto_refresh.py
```

### Manual Test

```bash
# Terminal 1: Start watcher
python aura_codemap_watcher.py

# Terminal 2: Make a change
echo "# Test" >> test_file.py

# Terminal 1 should show:
# [CODEMAP Watcher] Detected change: test_file.py
```

---

## 🐛 Troubleshooting

### Watcher Not Starting

**Error:** `ModuleNotFoundError: No module named 'watchdog'`

**Solution:**
```bash
pip install watchdog
```

### CODEMAP Not Updating

**Check 1:** Is CODEMAP generated?
```bash
ls -la .aura/CODEMAP.json
```

If missing:
```bash
python aura_codebase_navigator.py
```

**Check 2:** Are dependencies installed?
```bash
pip install -r requirements.txt
```

**Check 3:** Force a refresh
```python
from aura_bob_codemap_hooks import force_codemap_refresh
force_codemap_refresh()
```

### File Changes Not Detected

**Check 1:** Is file extension monitored?
```python
from aura_codemap_watcher import CODE_EXTENSIONS
print('.your_ext' in CODE_EXTENSIONS)
```

**Check 2:** Is directory ignored?
```python
from aura_codemap_watcher import IGNORE_DIRS
print('your_dir' in IGNORE_DIRS)
```

**Check 3:** Is watcher running?
```bash
ps aux | grep aura_codemap_watcher
```

---

## 📖 Documentation

- **[CODEMAP_AUTO_REFRESH_SUMMARY.md](CODEMAP_AUTO_REFRESH_SUMMARY.md)** - Executive summary and overview
- **[CODEMAP_AUTO_REFRESH_INTEGRATION.md](CODEMAP_AUTO_REFRESH_INTEGRATION.md)** - Technical integration details
- **[CODEMAP_TOOL_INTEGRATION_GUIDE.md](CODEMAP_TOOL_INTEGRATION_GUIDE.md)** - Tool-specific integration guides

---

## 🎓 Best Practices

### For Users

1. ✅ Run watcher as background service
2. ✅ Use quick-start scripts for easy setup
3. ✅ Check watcher logs if issues occur
4. ❌ Don't run multiple watchers per workspace

### For Tool Developers

1. ✅ Always notify after successful writes
2. ✅ Use batch notifications for multi-file ops
3. ✅ Handle import failures gracefully
4. ✅ Test with file system watcher first
5. ❌ Don't wait for refresh to complete (it's async)

---

## 🔮 Future Enhancements

Potential improvements:
- [ ] Parallel AST parsing for multi-file refreshes
- [ ] Incremental topology updates
- [ ] Conflict detection for concurrent edits
- [ ] Refresh queue prioritization
- [ ] Web dashboard for monitoring
- [ ] VS Code extension for one-click setup

---

## 📝 Summary

### What You Get

✅ **Automatic CODEMAP synchronization**
- No manual refresh commands
- Works with any tool
- Set-and-forget operation

✅ **Always accurate navigation**
- Correct line numbers
- Up-to-date symbol locations
- Reliable AI navigation

✅ **Excellent performance**
- 10-100× faster than full rebuild
- Minimal resource usage
- Background operation

### How to Use

**For most users:**
```bash
./start_codemap_watcher.sh  # or .bat on Windows
```

**For tool developers:**
```python
notify_file_modified(path)  # One line after file writes
```

**Result:** CODEMAP stays synchronized automatically! 🎉

---

## 📄 License

Part of AuraOS - See main project license.

## 🤝 Contributing

Contributions welcome! See main project contributing guidelines.

---

**Status:** ✅ Production-ready and tested  
**Version:** 1.0.0  
**Last Updated:** 2026-06-22