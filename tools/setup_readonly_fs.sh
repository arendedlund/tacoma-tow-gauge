#!/usr/bin/env bash
# Configure Raspberry Pi OS for a read-only root filesystem using overlayFS.
# Run once as root on the CM5.  Reboot after completion.
#
# Usage:
#   sudo bash tools/setup_readonly_fs.sh          # enable read-only root
#   sudo bash tools/setup_readonly_fs.sh --revert # restore read-write root
#
# What this does:
#   - Enables the official Raspberry Pi overlayFS read-only rootfs feature
#   - Mounts a small separate partition RW at /opt/gauge/config for threshold edits
#   - Gauge config survives reboot; OS filesystem survives unclean power-off

set -euo pipefail

REVERT=false
[[ "${1:-}" == "--revert" ]] && REVERT=true

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: run as root (sudo bash $0)"
    exit 1
fi

if ! command -v raspi-config &>/dev/null; then
    echo "ERROR: raspi-config not found — this script targets Raspberry Pi OS only."
    exit 1
fi

CONFIG_PART="${CONFIG_PARTITION:-/dev/mmcblk0p3}"

if $REVERT; then
    echo "Reverting to read-write root..."
    raspi-config nonint disable_overlayfs
    echo "Done — reboot to apply."
    exit 0
fi

echo "Enabling overlayFS read-only root..."
raspi-config nonint enable_overlayfs

# Mount the gauge config partition read-write at each boot
FSTAB_ENTRY="${CONFIG_PART}  /opt/gauge/config  ext4  defaults,noatime  0  2"
if ! grep -qF "$CONFIG_PART" /etc/fstab; then
    echo "$FSTAB_ENTRY" >> /etc/fstab
    echo "Added config partition to /etc/fstab: $CONFIG_PART"
else
    echo "Config partition already in /etc/fstab — skipping."
fi

mkdir -p /opt/gauge/config

echo ""
echo "Done.  Reboot to apply read-only root."
echo "Config files at /opt/gauge/config remain writable after reboot."
echo ""
echo "To revert: sudo bash tools/setup_readonly_fs.sh --revert"
