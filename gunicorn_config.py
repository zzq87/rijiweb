import os
import multiprocessing

bind = "127.0.0.1:8000"
workers = 2
threads = 2
worker_class = "sync"
worker_connections = 100
timeout = 60
graceful_timeout = 10
keepalive = 5

max_requests = 500
max_requests_jitter = 50

loglevel = "info"
accesslog = "-"
errorlog = "-"

user = os.environ.get("DIARY_USER", None)
group = os.environ.get("DIARY_GROUP", None)

preload_app = True

raw_env = [
    "DIARY_ENV=production",
]
