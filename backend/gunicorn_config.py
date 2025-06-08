# Gunicorn configuration for production deployment
# Optimized for 100+ concurrent users

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('API_PORT', '8000')}"
backlog = 2048

# Worker processes
# Use 2-4 workers per CPU core for async workers
workers = multiprocessing.cpu_count() * 2
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'thanotopolis-backend'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL/TLS (uncomment for HTTPS)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# StatsD integration (uncomment for monitoring)
# statsd_host = 'localhost:8125'
# statsd_prefix = 'thanotopolis'

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawning (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Listening at: %s", server.cfg.bind)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("Shutting down: Master")