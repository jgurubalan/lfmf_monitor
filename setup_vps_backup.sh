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
#   2. Ask for VPS information
#   3. Create a dedicated SSH key
#   4. Install the public key on the VPS
#   5. Configure ~/.ssh/config
#   6. Create the remote backup directory
#   7. Test passwordless SSH
#   8. Test an actual file transfer
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
echo "    watchdog backup directory"
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
echo "STEP 1 - Checking required SSH programs"
echo "------------------------------------------------------------"
echo

for command in ssh ssh-keygen ssh-copy-id scp; do

    if command -v "$command" >/dev/null 2>&1; then
        echo "OK: $command"
    else
        echo "ERROR: '$command' was not found."
        echo
        echo "Install the OpenSSH client before continuing."
        exit 1
    fi

done

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

DEFAULT_VPS_PATH="~/projects/lfmf_monitoring/data/backups/watchdog"

read -rp \
    "Remote backup directory [$DEFAULT_VPS_PATH]: " \
    VPS_PATH

VPS_PATH="${VPS_PATH:-$DEFAULT_VPS_PATH}"

# ============================================================
# Display configuration
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 3 - Configuration"
echo "------------------------------------------------------------"
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
echo "Remote backup directory:"
echo "    $VPS_PATH"
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
# Create remote backup directory
# ============================================================

echo
echo "------------------------------------------------------------"
echo "STEP 9 - Creating VPS backup directory"
echo "------------------------------------------------------------"
echo
echo "Creating:"
echo
echo "    $VPS_PATH"
echo

ssh "$SSH_ALIAS" \
    "mkdir -p '$VPS_PATH'"

echo
echo "OK: Remote backup directory created."

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
echo "Copying test file to VPS..."

scp \
    "$TEST_FILE" \
    "$SSH_ALIAS:$VPS_PATH/"

rm -f "$TEST_FILE"

echo
echo "OK: File transfer completed."

# ============================================================
# Verify test file on VPS
# ============================================================

echo
echo "Verifying test file on VPS..."

if ssh "$SSH_ALIAS" \
    "test -f '$VPS_PATH/$REMOTE_TEST_FILE'"
then

    echo "OK: VPS received the test file."

else

    echo "ERROR: Test file was not found on VPS."
    exit 1
fi

# ============================================================
# Remove test file
# ============================================================

echo
echo "Removing temporary test file from VPS..."

ssh "$SSH_ALIAS" \
    "rm -f '$VPS_PATH/$REMOTE_TEST_FILE'"

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
echo "Backup directory:"
echo "    $VPS_PATH"
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