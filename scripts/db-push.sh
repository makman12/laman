#!/bin/bash
set -e

SERVER="mali@193.205.136.58"
REMOTE_DIR="/home/mali/laman"
LOCAL_PATH="$(dirname "$0")/../db.sqlite3"

echo "WARNING: This will overwrite the production database."
echo "Any data entered on production since your last pull will be lost."
echo ""
read -p "Type 'yes' to confirm: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

if [ ! -f "$LOCAL_PATH" ]; then
    echo "Error: No local db.sqlite3 found."
    exit 1
fi

# Back up remote DB first
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "Backing up remote database..."
ssh "$SERVER" "mkdir -p $REMOTE_DIR/backups && cp $REMOTE_DIR/db.sqlite3 $REMOTE_DIR/backups/db.sqlite3.$TIMESTAMP"
echo "Remote backup created: backups/db.sqlite3.$TIMESTAMP"

# Push local DB
echo "Uploading database..."
scp "$LOCAL_PATH" "$SERVER:$REMOTE_DIR/db.sqlite3"

# Restart gunicorn
echo "Restarting gunicorn..."
ssh "$SERVER" "sudo systemctl restart gunicorn"

echo "Database pushed and server restarted successfully."
