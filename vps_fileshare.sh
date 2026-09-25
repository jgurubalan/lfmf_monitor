#!/usr/bin/env bash

set -e

VPS_USER="jgurubalan"
VPS_HOST="169.58.129.177"

echo "======================================"
echo "       VPS File Transfer Utility"
echo "======================================"
echo
echo "VPS: ${VPS_USER}@${VPS_HOST}"
echo

echo "1) Upload: node-oscar -> VPS"
echo "2) Download: VPS -> node-oscar"
echo
read -rp "Choose [1/2]: " DIRECTION

case "$DIRECTION" in
    1)
        echo
        read -rp "Local file/directory path: " LOCAL_PATH
        LOCAL_PATH="${LOCAL_PATH/#\~/$HOME}"

        if [[ ! -e "$LOCAL_PATH" ]]; then
            echo "ERROR: '$LOCAL_PATH' does not exist."
            exit 1
        fi

        read -rp "Remote destination directory [~/projects/lfmf_monitoring]: " REMOTE_DIR

        if [[ -z "$REMOTE_DIR" ]]; then
            REMOTE_DIR="~/projects/lfmf_monitoring"
        fi

        echo
        echo "Uploading:"
        echo "  From: $LOCAL_PATH"
        echo "  To:   ${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}"
        echo

        read -rp "Continue? [y/N]: " CONFIRM

        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            scp -r "$LOCAL_PATH" "${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}/"
            echo
            echo "Upload complete."
        else
            echo "Cancelled."
        fi
        ;;

    2)
        echo
        read -rp "Remote file/directory path: " REMOTE_PATH

        if [[ -z "$REMOTE_PATH" ]]; then
            echo "ERROR: Remote path cannot be empty."
            exit 1
        fi

        read -rp "Local destination directory [$PWD]: " LOCAL_DIR

        if [[ -z "$LOCAL_DIR" ]]; then
            LOCAL_DIR="$PWD"
        fi

        LOCAL_DIR="${LOCAL_DIR/#\~/$HOME}"

        if [[ ! -d "$LOCAL_DIR" ]]; then
            echo "ERROR: Local directory '$LOCAL_DIR' does not exist."
            exit 1
        fi

        echo
        echo "Downloading:"
        echo "  From: ${VPS_USER}@${VPS_HOST}:${REMOTE_PATH}"
        echo "  To:   $LOCAL_DIR"
        echo

        read -rp "Continue? [y/N]: " CONFIRM

        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            scp -r "${VPS_USER}@${VPS_HOST}:${REMOTE_PATH}" "$LOCAL_DIR/"
            echo
            echo "Download complete."
        else
            echo "Cancelled."
        fi
        ;;

    *)
        echo "Invalid choice."
        exit 1
        ;;
esac
