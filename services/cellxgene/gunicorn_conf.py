"""
Gunicorn Configuration for CellXGene Service

Constitutional Alignment:
- Principle III (Code Clarity): Well-documented configuration
"""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5005"
backlog = 2048

# Worker processes
workers = int(os.getenv('WORKERS', '2'))
worker_class = 'uvicorn.workers.UvicornWorker'
worker_connections = 1000
timeout = int(os.getenv('TIMEOUT', '300'))
keepalive = 5

# Memory management
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'cellxgene-service'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (for future use)
keyfile = None
certfile = None

print(f"Gunicorn configured with {workers} workers")
