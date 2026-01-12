# LAMAN Deployment Guide for Debian Server

## Overview
Deploy LAMAN (Hittite Names Database) to laman.hittites.org using nginx + gunicorn.

---

## 1. Server Preparation

### Update system
```bash
sudo apt update && sudo apt upgrade -y
```

### Install required packages
```bash
sudo apt install -y python3 python3-pip python3-venv nginx git
```

### Create directories
```bash
sudo mkdir -p /var/www/laman
sudo mkdir -p /run/gunicorn
sudo mkdir -p /var/log/gunicorn
sudo chown www-data:www-data /var/www/laman
sudo chown www-data:www-data /run/gunicorn
sudo chown www-data:www-data /var/log/gunicorn
```

---

## 2. Get the Code

### Option A: Clone from GitHub
```bash
cd /var/www
sudo -u www-data git clone https://github.com/YOUR_USERNAME/laman.git
```

### Option B: Upload directly
```bash
# From your local machine:
scp -r LamanV3/* user@your-server:/var/www/laman/
```

---

## 3. Setup Python Environment

```bash
cd /var/www/laman

# Create virtual environment
sudo -u www-data python3 -m venv venv

# Activate and install dependencies
sudo -u www-data ./venv/bin/pip install --upgrade pip
sudo -u www-data ./venv/bin/pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

```bash
cd /var/www/laman

# Copy example and edit
sudo -u www-data cp .env.example .env
sudo -u www-data nano .env
```

**Generate a new SECRET_KEY:**
```bash
./venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Edit `.env`:**
```
SECRET_KEY=your-generated-key-here
DEBUG=False
ALLOWED_HOSTS=laman.hittites.org,www.laman.hittites.org
```

---

## 5. Upload Database

The SQLite database (`db.sqlite3`) is not in git. Upload it separately:

```bash
# From your local machine:
scp db.sqlite3 user@your-server:/var/www/laman/

# On server, set permissions:
sudo chown www-data:www-data /var/www/laman/db.sqlite3
```

---

## 6. Collect Static Files

```bash
cd /var/www/laman
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput
```

This creates `staticfiles/` directory. WhiteNoise will serve these automatically.

---

## 7. Setup Gunicorn Service

```bash
# Copy service files
sudo cp deploy/gunicorn-laman.socket /etc/systemd/system/
sudo cp deploy/gunicorn-laman.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable gunicorn-laman.socket
sudo systemctl start gunicorn-laman.socket
sudo systemctl enable gunicorn-laman.service
sudo systemctl start gunicorn-laman.service
```

**Check status:**
```bash
sudo systemctl status gunicorn-laman.service
```

---

## 8. Setup Nginx

```bash
# Copy config
sudo cp deploy/nginx.conf /etc/nginx/sites-available/laman

# Enable site
sudo ln -s /etc/nginx/sites-available/laman /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## 9. Setup SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d laman.hittites.org -d www.laman.hittites.org

# Auto-renewal is set up automatically
```

---

## 10. Firewall (if using ufw)

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable
```

---

## Maintenance Commands

### Restart application
```bash
sudo systemctl restart gunicorn-laman.service
```

### View logs
```bash
# Gunicorn logs
sudo journalctl -u gunicorn-laman.service

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Update code from GitHub
```bash
cd /var/www/laman
sudo -u www-data git pull
sudo -u www-data ./venv/bin/pip install -r requirements.txt
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput
sudo -u www-data ./venv/bin/python manage.py migrate
sudo systemctl restart gunicorn-laman.service
```

### Django shell
```bash
cd /var/www/laman
sudo -u www-data ./venv/bin/python manage.py shell
```

### Create superuser
```bash
cd /var/www/laman
sudo -u www-data ./venv/bin/python manage.py createsuperuser
```

---

## Troubleshooting

### Check if gunicorn is running
```bash
sudo systemctl status gunicorn-laman.service
```

### Check socket
```bash
ls -la /run/gunicorn/laman.sock
```

### Test gunicorn directly
```bash
cd /var/www/laman
sudo -u www-data ./venv/bin/gunicorn --bind 0.0.0.0:8000 laman.wsgi:application
```

### Permission issues
```bash
sudo chown -R www-data:www-data /var/www/laman
```

### SELinux issues (if applicable)
```bash
sudo setsebool -P httpd_can_network_connect 1
```

---

## File Structure on Server

```
/var/www/laman/
├── db.sqlite3           # Database (uploaded separately)
├── .env                 # Environment variables (not in git)
├── manage.py
├── requirements.txt
├── gunicorn.conf.py
├── venv/                # Python virtual environment
├── staticfiles/         # Collected static files (created by collectstatic)
├── laman/               # Django project settings
├── namefinder/          # Main Django app
└── deploy/              # Deployment configs (for reference)
```
