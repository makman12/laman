#!/bin/bash
set -e

SERVER="mali@193.205.136.58"
REMOTE_PATH="/home/mali/laman/db.sqlite3"
LOCAL_PATH="$(dirname "$0")/../db.sqlite3"

echo "Pulling production database..."

# Back up existing local DB if it exists
if [ -f "$LOCAL_PATH" ]; then
    cp "$LOCAL_PATH" "$LOCAL_PATH.bak"
    echo "Backed up local DB to db.sqlite3.bak"
fi

scp "$SERVER:$REMOTE_PATH" "$LOCAL_PATH"
echo "Database pulled successfully."
echo ""
echo "Reminder: if you have pending local migrations, run:"
echo "  python manage.py migrate"
