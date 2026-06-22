# CODEMAP Auto-Refresh: Tool Integration Guide

## Overview

This guide explains how to integrate CODEMAP auto-refresh with various development tools and AI coding assistants. The system supports two integration methods:

1. **File System Watcher** (Universal) - Works with ANY tool automatically
2. **Direct Integration** (Optimal) - Explicit notification from tool code

## Method 1: File System Watcher (Recommended for Most Users)

### What It Does

The file system watcher monitors your workspace and automatically detects code changes from **any source**:

- ✅ Bob AI file modifications
- ✅ VS Code edits
- ✅ Cline/Claude Dev edits
- ✅ Cursor AI edits
- ✅ Manual file edits
- ✅ Git operations
- ✅ Command-line tools
- ✅ Any other editor or tool

### Installation

```bash
# Install watchdog library
pip install watchdog

# Or add to requirements.txt
echo "watchdog>=3.0.0" >> requirements.txt
pip install -r requirements.txt
```

### Usage

#### Option A: Run as Background Service

```bash
# Start the watcher (runs in foreground)
python aura_codemap_watcher.py

# Or run in background (Linux/Mac)
nohup python aura_codemap_watcher.py > codemap_watcher.log 2>&1 &

# Or run in background (Windows PowerShell)
Start-Process python -ArgumentList "aura_codemap_watcher.py" -WindowStyle Hidden
```

#### Option B: Integrate into Your Application

```python
from aura_codemap_watcher import start_watcher, stop_watcher

# Start monitoring
watcher = start_watcher(workspace_path=".", debounce_seconds=0.5)

# Your application runs...

# Stop monitoring when done
stop_watcher()
```

#### Option C: Run as Daemon/Service

Create a systemd service (Linux):

```ini
# /etc/systemd/system/codemap-watcher.service
[Unit]
Description=CODEMAP File System Watcher
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/AuraOS
ExecStart=/usr/bin/python3 /path/to/AuraOS/aura_codemap_watcher.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable codemap-watcher
sudo systemctl start codemap-watcher
sudo systemctl status codemap-watcher
```

### Configuration

```python
from aura_codemap_watcher import start_watcher

# Custom configuration
watcher = start_watcher(
    workspace_path="/path/to/project",  # Workspace to monitor
    debounce_seconds=0.5                # Min time between events
)
```

### Monitored File Types

- Python: `.py`
- Rust: `.rs`
- C/C++: `.c`, `.cpp`, `.h`, `.hpp`
- JavaScript/TypeScript: `.js`, `.ts`
- Java: `.java`
- Go: `.go`
- Ruby: `.rb`
- PHP: `.php`

### Ignored Directories

- `.git`, `__pycache__`, `.pytest_cache`
- `node_modules`, `.venv`, `venv`
- `.aura`, `Aura_Memory`
- `.vscode`, `.idea`
- `build`, `dist`, `target`

---

## Method 2: Direct Integration (Optimal Performance)

For tool developers who want explicit control and minimal latency.

### For Bob AI Integration

#### Step 1: Import the Hook

```python
from aura_bob_codemap_hooks import notify_file_modified
```

#### Step 2: Add Notification to File Tools

**In `write_to_file` tool:**
```python
def write_to_file(path: str, content: str, line_count: int):
    """Write content to a file."""
    # Existing write logic
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Notify CODEMAP system
    notify_file_modified(path)
    
    return {"status": "success", "path": path}
```

**In `apply_diff` tool:**
```python
def apply_diff(path: str, diff: str):
    """Apply a diff to a file."""
    # Existing diff application logic
    apply_patch(path, diff)
    
    # Notify CODEMAP system
    notify_file_modified(path)
    
    return {"status": "success", "path": path}
```

**In `insert_content` tool:**
```python
def insert_content(path: str, line: int, content: str):
    """Insert content at a specific line."""
    # Existing insert logic
    insert_at_line(path, line, content)
    
    # Notify CODEMAP system
    notify_file_modified(path)
    
    return {"status": "success", "path": path}
```

#### Step 3: Handle Batch Operations

```python
from aura_bob_codemap_hooks import notify_files_modified

def refactor_codebase(files: list[str]):
    """Refactor multiple files."""
    modified_files = []
    
    for file in files:
        # Modify file
        modify_file(file)
        modified_files.append(file)
    
    # Notify all at once (more efficient)
    notify_files_modified(modified_files)
    
    return {"status": "success", "files": modified_files}
```

### For VS Code Extension Integration

#### JavaScript/TypeScript Extension

```typescript
// Import Node.js child_process
import { exec } from 'child_process';
import * as vscode from 'vscode';

// After file save
vscode.workspace.onDidSaveTextDocument((document) => {
    const filePath = document.fileName;
    
    // Check if it's a code file
    if (isCodeFile(filePath)) {
        // Call Python notification hook
        exec(`python -c "from aura_bob_codemap_hooks import notify_file_modified; notify_file_modified('${filePath}')"`,
            (error, stdout, stderr) => {
                if (error) {
                    console.error(`CODEMAP notification failed: ${error}`);
                }
            }
        );
    }
});

function isCodeFile(path: string): boolean {
    const codeExtensions = ['.py', '.rs', '.c', '.cpp', '.js', '.ts', '.java', '.go'];
    return codeExtensions.some(ext => path.endsWith(ext));
}
```

#### Alternative: Use File System Watcher

VS Code extensions can also use the file system watcher approach (Method 1) without any code changes.

### For Cline/Claude Dev Integration

#### Option 1: Modify Cline's File Operations

If you have access to Cline's source code:

```typescript
// In Cline's file write function
async function writeFile(path: string, content: string): Promise<void> {
    // Existing write logic
    await fs.writeFile(path, content);
    
    // Notify CODEMAP
    await notifyCodeMap(path);
}

async function notifyCodeMap(path: string): Promise<void> {
    try {
        const { exec } = require('child_process');
        exec(`python -c "from aura_bob_codemap_hooks import notify_file_modified; notify_file_modified('${path}')"`);
    } catch (error) {
        // Silently fail - don't break Cline's operations
        console.debug('CODEMAP notification failed:', error);
    }
}
```

#### Option 2: Use File System Watcher

Simply run the file system watcher alongside Cline. No code changes needed.

### For Cursor AI Integration

Cursor AI uses VS Code as its base, so use the VS Code integration method or file system watcher.

### For Command-Line Tools

#### Git Hooks

Add to `.git/hooks/post-commit`:

```bash
#!/bin/bash
# Notify CODEMAP after commit

python -c "
from aura_bob_codemap_hooks import force_codemap_refresh
force_codemap_refresh()
print('CODEMAP refreshed after commit')
"
```

Make executable:
```bash
chmod +x .git/hooks/post-commit
```

#### Custom Scripts

```python
#!/usr/bin/env python3
"""My custom code modification script."""

from aura_bob_codemap_hooks import notify_file_modified

def modify_files():
    files_modified = []
    
    # Your file modification logic
    for file in get_files_to_modify():
        modify_file(file)
        files_modified.append(file)
    
    # Notify CODEMAP
    for file in files_modified:
        notify_file_modified(file)

if __name__ == "__main__":
    modify_files()
```

---

## Integration Comparison

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **File System Watcher** | • Universal (works with any tool)<br>• No code changes needed<br>• Easy setup | • Slight delay (0.5s debounce)<br>• Requires watchdog library | Most users, mixed tooling |
| **Direct Integration** | • Immediate notification<br>• No external dependencies<br>• Explicit control | • Requires code changes<br>• Tool-specific | Tool developers, performance-critical |

---

## Testing Your Integration

### Test File System Watcher

```bash
# Terminal 1: Start watcher
python aura_codemap_watcher.py

# Terminal 2: Make a change
echo "# Test change" >> test_file.py

# Terminal 1 should show:
# [CODEMAP Watcher] Detected change: test_file.py
```

### Test Direct Integration

```python
from aura_bob_codemap_hooks import notify_file_modified
import time

# Modify a file
with open("test_file.py", "w") as f:
    f.write("# Test content\n")

# Notify system
notify_file_modified("test_file.py")

# Wait for batch refresh
time.sleep(3)

# Check CODEMAP was updated
import json
codemap = json.load(open(".aura/CODEMAP.json"))
print(f"Last refresh: {codemap['summary']['last_incremental_refresh_unix']}")
```

---

## Troubleshooting

### File System Watcher Not Detecting Changes

**Check 1:** Is watchdog installed?
```bash
pip list | grep watchdog
```

**Check 2:** Is watcher running?
```bash
ps aux | grep aura_codemap_watcher
```

**Check 3:** Is file type monitored?
```python
# Check if your file extension is in CODE_EXTENSIONS
from aura_codemap_watcher import CODE_EXTENSIONS
print('.your_ext' in CODE_EXTENSIONS)
```

### Direct Integration Not Working

**Check 1:** Can you import the hook?
```python
try:
    from aura_bob_codemap_hooks import notify_file_modified
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
```

**Check 2:** Is CODEMAP generated?
```bash
ls -la .aura/CODEMAP.json
```

If missing:
```bash
python aura_codebase_navigator.py
```

### CODEMAP Not Updating

**Check 1:** Are dependencies installed?
```bash
pip install -r requirements.txt
```

**Check 2:** Force a refresh:
```python
from aura_bob_codemap_hooks import force_codemap_refresh
force_codemap_refresh()
```

---

## Best Practices

### For Tool Developers

1. ✅ **Always notify after successful writes** - Even if unsure
2. ✅ **Use batch notifications for multi-file ops** - More efficient
3. ✅ **Handle import failures gracefully** - Don't break your tool
4. ✅ **Test with file system watcher first** - Verify it works
5. ❌ **Don't wait for refresh to complete** - It's async

### For Users

1. ✅ **Use file system watcher for mixed tooling** - Simplest approach
2. ✅ **Run watcher as background service** - Set and forget
3. ✅ **Check watcher logs if issues occur** - Debugging info
4. ❌ **Don't run multiple watchers** - One per workspace

---

## Performance Impact

### File System Watcher

- **CPU:** <1% idle, <5% during file operations
- **Memory:** ~20-50MB
- **Latency:** 0.5-1.0 seconds (debounced)
- **I/O:** Minimal (only monitors, doesn't read files)

### Direct Integration

- **CPU:** Negligible (<0.1%)
- **Memory:** Negligible (<1MB)
- **Latency:** Immediate (0-2 seconds batched refresh)
- **I/O:** Only on actual file modifications

---

## Example Integrations

### Complete Bob AI Integration

```python
# bob_tools.py
from aura_bob_codemap_hooks import notify_file_modified, notify_files_modified

class BobFileTools:
    def write_to_file(self, path: str, content: str, line_count: int):
        with open(path, 'w') as f:
            f.write(content)
        notify_file_modified(path)
        return {"status": "success"}
    
    def apply_diff(self, path: str, diff: str):
        self._apply_patch(path, diff)
        notify_file_modified(path)
        return {"status": "success"}
    
    def refactor_files(self, files: list[str]):
        for file in files:
            self._refactor_file(file)
        notify_files_modified(files)
        return {"status": "success"}
```

### Complete VS Code Extension

```typescript
// extension.ts
import * as vscode from 'vscode';
import { exec } from 'child_process';

export function activate(context: vscode.ExtensionContext) {
    // Monitor file saves
    const saveWatcher = vscode.workspace.onDidSaveTextDocument((doc) => {
        notifyCodeMap(doc.fileName);
    });
    
    context.subscriptions.push(saveWatcher);
}

function notifyCodeMap(filePath: string): void {
    const codeExts = ['.py', '.rs', '.c', '.cpp', '.js', '.ts'];
    if (!codeExts.some(ext => filePath.endsWith(ext))) {
        return;
    }
    
    exec(
        `python -c "from aura_bob_codemap_hooks import notify_file_modified; notify_file_modified('${filePath}')"`,
        (error) => {
            if (error) {
                console.debug('CODEMAP notification failed:', error);
            }
        }
    );
}
```

---

## Summary

**Recommended Approach:**

1. **For most users:** Use file system watcher (Method 1)
   - Run: `python aura_codemap_watcher.py`
   - Works with all tools automatically

2. **For tool developers:** Add direct integration (Method 2)
   - One line: `notify_file_modified(path)`
   - Optimal performance

3. **For production:** Run watcher as system service
   - Set up systemd/launchd service
   - Automatic startup on boot

**Result:** CODEMAP stays synchronized automatically, regardless of which tool modifies files.