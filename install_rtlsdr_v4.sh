#!/usr/bin/env bash

set -euo pipefail

echo "=========================================="
echo "     RTL-SDR Blog V4 Installation"
echo "=========================================="
echo

# --------------------------------------------------
# Configuration
# --------------------------------------------------

REPO_DIR="$HOME/rtl-sdr-blog"

# --------------------------------------------------
# Check root/sudo
# --------------------------------------------------

if ! command -v sudo >/dev/null 2>&1; then
    echo "ERROR: sudo is not installed."
    exit 1
fi

# --------------------------------------------------
# Update system
# --------------------------------------------------

echo "[1/9] Updating package lists..."
sudo apt update

# --------------------------------------------------
# Install dependencies
# --------------------------------------------------

echo
echo "[2/9] Installing build dependencies..."

sudo apt install -y \
    git \
    cmake \
    pkg-config \
    build-essential \
    libusb-1.0-0-dev \
    usbutils

# --------------------------------------------------
# Remove conflicting RTL-SDR packages
# --------------------------------------------------

echo
echo "[3/9] Removing conflicting RTL-SDR packages..."

sudo apt purge -y \
    librtlsdr-dev \
    librtlsdr0 \
    rtl-sdr \
    rtl-sdr-blog \
    2>/dev/null || true

# --------------------------------------------------
# Remove old installations
# --------------------------------------------------

echo
echo "[4/9] Removing old RTL-SDR installations..."

sudo rm -f \
    /usr/local/lib/librtlsdr* \
    /usr/local/bin/rtl_* \
    /usr/local/include/rtl-sdr.h \
    /usr/local/include/rtl-sdr_export.h

sudo ldconfig

# --------------------------------------------------
# Clone/update RTL-SDR Blog driver
# --------------------------------------------------

echo
echo "[5/9] Getting RTL-SDR Blog V4 driver..."

if [ -d "$REPO_DIR/.git" ]; then
    echo "Existing repository found."
    cd "$REPO_DIR"
    git pull
else
    rm -rf "$REPO_DIR"

    git clone \
        https://github.com/rtlsdrblog/rtl-sdr-blog.git \
        "$REPO_DIR"

    cd "$REPO_DIR"
fi

# --------------------------------------------------
# Build
# --------------------------------------------------

echo
echo "[6/9] Building RTL-SDR Blog driver..."

rm -rf build
mkdir build
cd build

cmake .. \
    -DINSTALL_UDEV_RULES=ON

make -j"$(nproc)"

# --------------------------------------------------
# Install
# --------------------------------------------------

echo
echo "[7/9] Installing RTL-SDR Blog driver..."

sudo make install

# Install udev rules if supplied by repository
if [ -f ../rtl-sdr.rules ]; then
    sudo cp ../rtl-sdr.rules /etc/udev/rules.d/rtl-sdr.rules
fi

sudo ldconfig

# --------------------------------------------------
# Blacklist DVB driver
# --------------------------------------------------

echo
echo "[8/9] Configuring DVB driver blacklist..."

sudo tee /etc/modprobe.d/blacklist-rtl-sdr.conf >/dev/null <<'EOF'
blacklist dvb_usb_rtl28xxu
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# --------------------------------------------------
# Verify installation
# --------------------------------------------------

echo
echo "[9/9] Verifying installation..."

echo
echo "Installed commands:"

command -v rtl_test || true
command -v rtl_sdr || true
command -v rtl_tcp || true

echo
echo "Driver version:"
rtl_test --version 2>&1 || true

echo
echo "USB RTL-SDR devices:"
lsusb | grep -Ei 'RTL|Realtek|2838|0bda' || true

echo
echo "=========================================="
echo "Installation complete."
echo "=========================================="
echo
echo "IMPORTANT:"
echo "Reboot the Raspberry Pi before testing the V4."
echo
echo "After reboot run:"
echo
echo "    rtl_test -t"
echo
echo "You should see:"
echo
echo "    RTL-SDR Blog V4 Detected"
echo "    Rafael Micro R828D tuner"
echo
