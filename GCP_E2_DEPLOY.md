# GCP e2-micro Deployment Guide

## Instance Requirements
- Machine type: e2-micro
- Memory: 1GB
- vCPU: 1 shared
- OS: Ubuntu 20.04 LTS

## System Setup
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python and dependencies
sudo apt-get install python3-pip python3-venv git nginx -y

# Install system dependencies
sudo apt-get install python3-dev build-essential -y

# Create app directory
mkdir -p /opt/recallai
cd /opt/recallai

# Clone your application
git clone [your-repo-url] .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psutil
```

## Memory Optimization
```bash
# Add to /etc/sysctl.conf
vm.swappiness=60
vm.vfs_cache_pressure=50

# Create swap file if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Environment Setup
```bash
# Create .env file
cp .env.example .env

# Configure environment variables
export MALLOC_ARENA_MAX=2
export PYTHONWARNINGS="ignore"
export TOKENIZERS_PARALLELISM=false
```

## Nginx Configuration
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 5M;
        proxy_read_timeout 120s;
    }
}
```

## Systemd Service
Create `/etc/systemd/system/recallai.service`:
```ini
[Unit]
Description=RecallAI Gunicorn Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/recallai
Environment="PATH=/opt/recallai/venv/bin"
Environment="MALLOC_ARENA_MAX=2"
Environment="PYTHONWARNINGS=ignore"
Environment="TOKENIZERS_PARALLELISM=false"
EnvironmentFile=/opt/recallai/.env
ExecStart=/opt/recallai/venv/bin/gunicorn -c gunicorn.conf.py "app:create_app()"
Restart=always
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
```

## Starting the Service
```bash
sudo systemctl daemon-reload
sudo systemctl start recallai
sudo systemctl enable recallai
```

## Monitoring
Monitor resource usage:
```bash
# Memory usage
watch -n 1 free -m

# Process status
ps aux | grep gunicorn

# Application logs
sudo journalctl -u recallai -f
```

## Performance Tips
1. Keep concurrent uploads limited to 3
2. Maximum file size: 5MB
3. Chunk size: 400 characters
4. Clean up every 15 minutes
5. Monitor memory usage
6. Use health check endpoint

## Troubleshooting
1. If memory usage is high:
   - Reduce MAX_UPLOADS
   - Decrease CHUNK_SIZE
   - Increase cleanup frequency

2. If service fails to start:
   - Check logs: `sudo journalctl -u recallai -f`
   - Verify permissions
   - Check memory usage

3. If response times are slow:
   - Reduce concurrent connections
   - Check CPU usage
   - Verify swap usage
