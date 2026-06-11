#!/bin/bash
echo "========================================="
echo " 🌌 AURA OS: SOVEREIGN EDGE SETUP 🌌 "
echo "========================================="

# 1. System Diagnostics
ARCH=$(uname -m)
TOTAL_RAM=$(grep MemTotal /proc/meminfo | awk '{print $2}')
RAM_GB=$((TOTAL_RAM / 1024 / 1024))

echo "[*] Diagnostics:"
echo "  -> Architecture: $ARCH"
echo "  -> Available RAM: ${RAM_GB}GB"
echo "-----------------------------------------"

# 2. Base Dependency Installation
echo "[*] Upgrading Termux environment..."
pkg update -y && pkg upgrade -y
pkg install python clang rust make libffi openssl termux-api -y

# 3. Python Matrix Build
echo "[*] Building Python computational matrix..."
pip install --upgrade pip
pip install numpy duckduckgo-search psutil

# 4. AOT WebAssembly Engine Binding
echo "[*] Linking Wasmtime Engine..."
if [ "$ARCH" = "aarch64" ]; then
    echo "  -> ARM64 detected. Forcing strict binary download..."
    pip install wasmtime --only-binary :all:
    
    # Failsafe for Android's aggressive dynamic linker
    ln -sf /data/data/com.termux/files/usr/lib/python3.11/site-packages/wasmtime/android-aarch64/_libwasmtime.so /data/data/com.termux/files/usr/lib/libwasmtime.so 2>/dev/null
else
    pip install wasmtime
fi

# 5. Dynamic Hardware Tuning
echo "-----------------------------------------"
echo "[*] Tuning OS variables based on hardware..."
if [ "$RAM_GB" -ge 6 ]; then
    echo "[+] High-tier device detected. Unlocking max hypervector memory."
    export AURA_MEMORY_TIER="HIGH"
else
    echo "[+] Standard edge node detected. Enforcing strict memory boundaries to prevent thermal throttling."
    export AURA_MEMORY_TIER="EDGE"
fi

# 6. File System Permissions
echo "[*] Locking execution permissions..."
chmod 755 wasm_binaries/*.cwasm

echo "========================================="
echo "[+] Installation Complete." 
echo "[+] Run 'termux-wake-lock' then 'python core/aura_node.py' to boot the swarm."
echo "========================================="
