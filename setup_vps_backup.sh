#!/bin/bash

set -e

# ============================================================
# LFMF Monitor - VPS Backup SSH Setup
#
# This script creates a dedicated SSH identity for:
#
#     Raspberry Pi -> LFMF Monitor VPS
#
# It will:
#   1. Check required SSH tools
#   2. Read station_id from receiver.yaml
#   3. Ask for VPS information
#   4. Create a dedicated SSH key
#   5. Install the public key on the VPS
#   6. Configure ~/.ssh/config
#   7. Create the remote station backup directory
#   8. Test passwordless SSH
#   9. Test an actual file transfer
#
# The private key NEVER leaves the Raspberry Pi.
# ============================================================

set -u

echo
echo "============================================================"
echo "       LFMF MONITOR - VPS BACKUP SETUP"
echo "============================================================"
echo
echo "This is a ONE-TIME setup for automatic VPS backups."
echo
echo "The setup will establish:"
echo
echo "    Raspberry Pi"
echo "        |"
echo "        | SSH public-key authentication"
echo "        v"
echo "    LFMF Monitor VPS"
echo "        |"
echo "        v"
echo "    watchdog/<station_id> backup directory"
echo
echo "A dedicated SSH key will be created:"
echo
echo "    ~/.ssh/lfmf_monitor_vps"
echo
echo "The PRIVATE key stays on this Raspberry Pi."
echo "Only the PUBLIC key is installed on the VPS."
echo

read -rp "Press Enter to continue, or Ctrl-C to cancel..."

# ============================================================
# Check required commands
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 1 - Checking required programs"
echo "------------------------------------------------------------"
echo

for command in ssh ssh-keygen ssh-copy-id scp python3; do

    if command -v "$command" >/dev/null 2>&1; then
        echo "OK: $command"
    else
        echo "ERROR: '$command' was not found."
        exit 1
    fi

done

# ============================================================
# Locate receiver.yaml
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECEIVER_CONFIG="$SCRIPT_DIR/config/receiver.yaml"

echo
echo "Receiver configuration:"
echo
echo "    $RECEIVER_CONFIG"
echo

if [ ! -f "$RECEIVER_CONFIG" ]; then
    echo "ERROR: receiver.yaml was not found."
    echo
    echo "Expected:"
    echo "    $RECEIVER_CONFIG"
    exit 1
fi

# ============================================================
# Read station_id from receiver.yaml
#
# Expected YAML:
#
# station:
#   station_id: "LFMF-01"
# ============================================================

STATION_ID=$(python3 - "$RECEIVER_CONFIG" <<'PY'
import sys
import yaml

config_file = sys.argv[1]

with open(config_file, "r") as f:
    config = yaml.safe_load(f) or {}

station = config.get("station", {})
station_id = station.get("station_id")

if not station_id:
    print("ERROR: station.station_id not found in receiver.yaml",
          file=sys.stderr)
    sys.exit(1)

print(station_id)
PY
)

if [ -z "$STATION_ID" ]; then
    echo "ERROR: station_id is empty."
    exit 1
fi

echo "Station ID read from receiver.yaml:"
echo
echo "    $STATION_ID"
echo

# ============================================================
# LFMF Monitor SSH identity
# ============================================================

SSH_ALIAS="lfmf-monitor-vps"
KEY_FILE="$HOME/.ssh/lfmf_monitor_vps"

# ============================================================
# VPS information
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 2 - VPS information"
echo "------------------------------------------------------------"
echo
echo "Enter the VPS details below."
echo
echo "The current project VPS defaults are:"
echo
echo "    Host:     169.58.129.177"
echo "    User:     jgurubalan"
echo
echo "Press Enter to accept a default."
echo

read -rp "VPS hostname/IP [169.58.129.177]: " VPS_HOST
VPS_HOST="${VPS_HOST:-169.58.129.177}"

read -rp "VPS username [jgurubalan]: " VPS_USER
VPS_USER="${VPS_USER:-jgurubalan}"

# Use an absolute path.
#
# This avoids problems with '~' being inside quotes when
# the path is used by ssh commands.
DEFAULT_VPS_PATH="/home/${VPS_USER}/projects/lfmf_monitoring/data/backups/watchdog"

read -rp \
    "Remote backup directory [$DEFAULT_VPS_PATH]: " \
    VPS_PATH

VPS_PATH="${VPS_PATH:-$DEFAULT_VPS_PATH}"

# Station-specific directory
REMOTE_STATION_PATH="$VPS_PATH/$STATION_ID"

# ============================================================
# Display configuration
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 3 - Configuration"
echo "------------------------------------------------------------"
echo
echo "Station ID:"
echo "    $STATION_ID"
echo
echo "Pi SSH key:"
echo "    $KEY_FILE"
echo
echo "SSH alias:"
echo "    $SSH_ALIAS"
echo
echo "VPS:"
echo "    $VPS_USER@$VPS_HOST"
echo
echo "Remote backup root:"
echo "    $VPS_PATH"
echo
echo "Station backup directory:"
echo "    $REMOTE_STATION_PATH"
echo

read -rp "Is this correct? [y/N]: " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo
    echo "Setup cancelled."
    exit 0
fi

# ============================================================
# Create ~/.ssh
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 4 - Preparing SSH directory"
echo "------------------------------------------------------------"
echo

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

echo "OK: $HOME/.ssh"

# ============================================================
# Create dedicated SSH key
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 5 - Creating LFMF Monitor SSH key"
echo "------------------------------------------------------------"
echo

if [ -f "$KEY_FILE" ]; then

    echo "The key already exists:"
    echo
    echo "    $KEY_FILE"
    echo
    echo "The existing key will be reused."

else

    echo "Creating:"
    echo
    echo "    $KEY_FILE"
    echo

    echo "IMPORTANT:"
    echo "This key will have NO passphrase."
    echo
    echo "This is required because the watchdog must be able"
    echo "to perform automatic backups without human input."
    echo

    ssh-keygen \
        -t ed25519 \
        -f "$KEY_FILE" \
        -N "" \
        -C "lfmf-monitor-vps"

    echo
    echo "OK: LFMF Monitor SSH key created."

fi

chmod 600 "$KEY_FILE"
chmod 644 "$KEY_FILE.pub"

echo
echo "Private key:"
echo "    $KEY_FILE"
echo
echo "Public key:"
echo "    $KEY_FILE.pub"
echo

# ============================================================
# Show public key fingerprint
# ============================================================

echo
echo "Public key fingerprint:"
echo

ssh-keygen -lf "$KEY_FILE.pub"

# ============================================================
# Install public key on VPS
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 6 - Installing public key on VPS"
echo "------------------------------------------------------------"
echo
echo "The following will happen:"
echo
echo "    Pi public key"
echo "          |"
echo "          v"
echo "    VPS ~/.ssh/authorized_keys"
echo
echo "The PRIVATE key will NOT be copied to the VPS."
echo
echo "You will probably be asked for the VPS user's password."
echo
echo "This password is needed only to authorize this initial"
echo "installation of the public key."
echo

read -rp "Press Enter to install the public key..."

ssh-copy-id \
    -i "$KEY_FILE.pub" \
    "$VPS_USER@$VPS_HOST"

echo
echo "OK: Public key installed on VPS."

# ============================================================
# Configure SSH
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 7 - Configuring SSH"
echo "------------------------------------------------------------"
echo

SSH_CONFIG="$HOME/.ssh/config"

touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

if grep -q "^Host $SSH_ALIAS$" "$SSH_CONFIG"; then

    echo "SSH alias '$SSH_ALIAS' already exists."
    echo "Existing configuration will be preserved."

else

    cat >> "$SSH_CONFIG" <<EOF

# ============================================================
# LFMF Monitor VPS backup
# ============================================================
Host $SSH_ALIAS
    HostName $VPS_HOST
    User $VPS_USER
    IdentityFile $KEY_FILE
    IdentitiesOnly yes
EOF

    echo "OK: SSH alias added."
fi

# ============================================================
# Test passwordless SSH
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 8 - Testing passwordless SSH"
echo "------------------------------------------------------------"
echo
echo "The Pi will now connect to:"
echo
echo "    $SSH_ALIAS"
echo
echo "No password should be requested."
echo

if ssh \
    -o BatchMode=yes \
    -o ConnectTimeout=10 \
    "$SSH_ALIAS" \
    "echo 'LFMF Monitor SSH authentication successful.'"
then

    echo
    echo "OK: Passwordless SSH is working."

else

    echo
    echo "ERROR: Passwordless SSH test failed."
    echo
    echo "The setup cannot continue until SSH authentication works."
    exit 1
fi

# ============================================================
# Create remote backup directories
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 9 - Creating VPS backup directories"
echo "------------------------------------------------------------"
echo

echo "Backup root:"
echo
echo "    $VPS_PATH"
echo

ssh "$SSH_ALIAS" \
    "mkdir -p '$VPS_PATH'"

echo "OK: Backup root created."

echo
echo "Station backup directory:"
echo
echo "    $REMOTE_STATION_PATH"
echo

ssh "$SSH_ALIAS" \
    "mkdir -p '$REMOTE_STATION_PATH'"

echo
echo "OK: Station backup directory created."

# ============================================================
# Test file transfer
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 10 - Testing actual file backup"
echo "------------------------------------------------------------"
echo

TEST_FILE="$HOME/lfmf_monitor/.lfmf_vps_backup_test"
REMOTE_TEST_FILE="$(basename "$TEST_FILE")"

echo "Creating temporary test file..."

echo "LFMF Monitor VPS backup test" \
    > "$TEST_FILE"

echo
echo "Local test file:"
echo
echo "    $TEST_FILE"
echo

echo "Remote destination:"
echo
echo "    $REMOTE_STATION_PATH/$REMOTE_TEST_FILE"
echo

echo "Copying test file to VPS..."

scp \
    "$TEST_FILE" \
    "$SSH_ALIAS:$REMOTE_STATION_PATH/"

rm -f "$TEST_FILE"

echo
echo "OK: File transfer completed."

# ============================================================
# Verify test file on VPS
# ============================================================

echo
echo "Verifying test file on VPS..."

if ssh "$SSH_ALIAS" \
    "test -f '$REMOTE_STATION_PATH/$REMOTE_TEST_FILE'"
then

    echo "OK: VPS received the test file."

else

    echo "ERROR: Test file was not found on VPS."
    echo
    echo "Expected location:"
    echo
    echo "    $REMOTE_STATION_PATH/$REMOTE_TEST_FILE"
    exit 1
fi

# ============================================================
# Verify file contents
# ============================================================

echo
echo "Verifying test file contents..."

REMOTE_CONTENT=$(ssh "$SSH_ALIAS" \
    "cat '$REMOTE_STATION_PATH/$REMOTE_TEST_FILE'")

if [ "$REMOTE_CONTENT" = "LFMF Monitor VPS backup test" ]; then

    echo "OK: File contents verified."

else

    echo "ERROR: File contents do not match."
    echo
    echo "Received:"
    echo "$REMOTE_CONTENT"
    exit 1
fi

# ============================================================
# Remove test file
# ============================================================

echo
echo "Removing temporary test file from VPS..."

ssh "$SSH_ALIAS" \
    "rm -f '$REMOTE_STATION_PATH/$REMOTE_TEST_FILE'"

echo "OK: Test file removed."

# ============================================================
# Final summary
# ============================================================

echo
echo
echo "============================================================"
echo "       LFMF MONITOR VPS BACKUP SETUP COMPLETE"
echo "============================================================"
echo
echo "Station ID:"
echo "    $STATION_ID"
echo
echo "SSH alias:"
echo "    $SSH_ALIAS"
echo
echo "SSH private key:"
echo "    $KEY_FILE"
echo
echo "SSH public key:"
echo "    $KEY_FILE.pub"
echo
echo "VPS:"
echo "    $VPS_USER@$VPS_HOST"
echo
echo "Backup root:"
echo "    $VPS_PATH"
echo
echo "Station backup directory:"
echo "    $REMOTE_STATION_PATH"
echo
echo "------------------------------------------------------------"
echo "EXPECTED VPS DIRECTORY"
echo "------------------------------------------------------------"
echo
echo "    $VPS_PATH/"
echo "        $STATION_ID/"
echo
echo "For your current receiver.yaml:"
echo
echo "    $VPS_PATH/LFMF-01/"
echo
echo "------------------------------------------------------------"
echo "IMPORTANT SECURITY INFORMATION"
echo "------------------------------------------------------------"
echo
echo "PRIVATE KEY:"
echo "    $KEY_FILE"
echo
echo "This file must remain ONLY on the Raspberry Pi."
echo "Never upload it to GitHub or copy it to the VPS."
echo
echo "PUBLIC KEY:"
echo "    $KEY_FILE.pub"
echo
echo "The public key has been installed in the VPS user's:"
echo
echo "    ~/.ssh/authorized_keys"
echo
echo "------------------------------------------------------------"
echo "MANUAL SSH TEST"
echo "------------------------------------------------------------"
echo
echo "You can now test the connection at any time with:"
echo
echo "    ssh $SSH_ALIAS"
echo
echo "------------------------------------------------------------"
echo "BACKUP TEST"
echo "------------------------------------------------------------"
echo
echo "The connection has already been tested with SCP."
echo
echo "The LFMF Monitor can now use this SSH connection for"
echo "automatic watchdog-log backups."
echo
echo "============================================================"
echo