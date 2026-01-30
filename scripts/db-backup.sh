#!/bin/bash
set -e

SERVER="mali@193.205.136.58"
REMOTE_DIR="/home/mali/laman"
LABEL="${1:-manual}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="db.sqlite3.${TIMESTAMP}_${LABEL}"

echo "Creating backup on server: backups/$BACKUP_NAME"
ssh "$SERVER" "mkdir -p $REMOTE_DIR/backups && cp $REMOTE_DIR/db.sqlite3 $REMOTE_DIR/backups/$BACKUP_NAME"
echo "Backup created successfully."
