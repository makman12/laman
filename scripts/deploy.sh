#!/bin/bash
set -e

SERVER="mali@193.205.136.58"
REMOTE_DIR="/home/mali/laman"

echo "Deploying to production..."

ssh "$SERVER" bash -s <<'EOF'
set -e
cd /home/mali/laman

# Back up DB before migrations
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p backups
cp db.sqlite3 "backups/db.sqlite3.$TIMESTAMP"
echo "Database backed up: backups/db.sqlite3.$TIMESTAMP"

# Move DB out of the way so git pull doesn't conflict
mv db.sqlite3 db.sqlite3.tmp 2>/dev/null || true

# Pull latest code
git pull --ff-only

# Move DB back
mv db.sqlite3.tmp db.sqlite3 2>/dev/null || true

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart gunicorn
sudo systemctl restart gunicorn-laman
EOF

echo "Deployment complete."
