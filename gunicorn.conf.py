# Gunicorn configuration file for LAMAN
# Run with: gunicorn -c gunicorn.conf.py laman.wsgi:application

import multiprocessing

# Bind to socket for nginx to connect
bind = "unix:/run/gunicorn/laman.sock"

# Alternative: bind to localhost port (if not using unix socket)
# bind = "127.0.0.1:8000"

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class
worker_class = "sync"

# Timeout for requests
timeout = 120

# Logging
accesslog = "/var/log/gunicorn/laman-access.log"
errorlog = "/var/log/gunicorn/laman-error.log"
loglevel = "info"

# Process naming
proc_name = "laman"

# Working directory
chdir = "/home/mali/laman"
