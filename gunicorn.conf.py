bind = "0.0.0.0:8080"  # Standard GCP port
workers = 1  # Single worker for e2-micro
threads = 2
worker_class = "gthread"
timeout = 120
keepalive = 5
max_requests = 100  # Reduced for memory management
max_requests_jitter = 20
accesslog = "-"
errorlog = "-"
loglevel = "info"
worker_tmp_dir = "/dev/shm"  # Use RAM for temp files
preload_app = True  # Load app before forking workers

# e2-micro optimizations
worker_connections = 50
backlog = 50

def worker_int(worker):
    worker.log.info("Shutting down worker gracefully")

def worker_exit(server, worker):
    import gc
    gc.collect()
