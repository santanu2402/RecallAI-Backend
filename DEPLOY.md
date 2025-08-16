# RecallAI Deployment Guide

## Prerequisites
- Python 3.8+
- Virtual environment
- Server with at least 2GB RAM
- Groq API key

## Environment Setup
1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install gunicorn  # For production deployment
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Production Deployment

### System Requirements
- Minimum 2GB RAM
- 2 CPU cores recommended
- 10GB disk space

### Starting the Server
```bash
gunicorn -c gunicorn.conf.py "app:create_app()"
```

### Environment Variables
- `GROQ_API_KEY`: Your Groq API key
- `UPLOAD_DIR`: Directory for file uploads (default: /tmp)
- `MAX_UPLOADS`: Maximum concurrent uploads (default: 5)
- `MAX_FILE_SIZE`: Maximum file size in bytes (default: 10MB)
- `CLEANUP_INTERVAL`: Cleanup interval in seconds (default: 1800)
- `CHUNK_SIZE`: Text chunk size (default: 500)
- `CHUNK_OVERLAP`: Chunk overlap size (default: 50)
- `PORT`: Server port (default: 5000)

### Memory Management
- The application uses auto-cleanup every 30 minutes
- Maximum memory usage is monitored
- Large files are automatically chunked

### Monitoring
- All operations are logged with timestamps
- Memory usage is tracked
- Error tracking is enabled
- Performance metrics are available

### Security Notes
- Set proper file permissions on upload directory
- Configure CORS settings if needed
- Use HTTPS in production
- Set appropriate file size limits

### Troubleshooting
Check logs for entries with these prefixes:
- `[STARTUP]`: Initialization issues
- `[ERROR]`: Error messages
- `[MEMORY]`: Memory usage alerts
- `[LIMIT]`: Resource limits reached
- `[CLEANUP]`: Cleanup operations
