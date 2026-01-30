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

# Pull latest code
git pull

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart gunicorn
sudo systemctl restart gunicorn
EOF

echo "Deployment complete."
