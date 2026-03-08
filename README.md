# LAMAN

A Django-based database for researching Hittite personal names, place names, and deities from cuneiform texts.


## Local Development

### Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/laman.git
cd laman

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

### Access

- Web interface: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- API: http://127.0.0.1:8000/api/

## Production Deployment

See [DEPLOY.md](DEPLOY.md) for full deployment instructions.



