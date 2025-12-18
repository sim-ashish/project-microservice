# Nginx Setup Guide

## Architecture

All services are now served through Nginx on **port 80**:

```
http://localhost/              → Frontend (port 3000)
http://localhost/auth/         → Auth Service (port 8000)
http://localhost/chat/         → Chat Service (port 8001)
ws://localhost/chat/ws/...     → WebSocket (port 8001)
```

## Starting Services

### 1. Start All Backend Services

**Terminal 1 - Auth Service:**
```bash
cd auth
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Chat Service:**
```bash
cd chat
uv run uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

**Terminal 3 - Frontend Service:**
```bash
cd frontend
uv run uvicorn server:app --host 127.0.0.1 --port 3000 --reload
```

**Terminal 4 (Optional) - Stream Service:**
```bash
cd stream
uv run uvicorn main:app --host 127.0.0.1 --port 8002 --reload
```

### 2. Start Nginx

Test the configuration first:
```bash
sudo nginx -t -c /home/ashish.chaudhary@simform.dom/Desktop/Microservice/nginx/nginx.conf
```

If the test passes, start nginx:
```bash
sudo nginx -c /home/ashish.chaudhary@simform.dom/Desktop/Microservice/nginx/nginx.conf
```

### 3. Reload Nginx (after config changes)

```bash
sudo nginx -s reload -c /home/ashish.chaudhary@simform.dom/Desktop/Microservice/nginx/nginx.conf
```

### 4. Stop Nginx

```bash
sudo nginx -s stop
```

## Access the Application

Open your browser and go to: **http://localhost**

The frontend will be served through nginx, and all API calls will be proxied to the backend services.

## Benefits of Using Nginx

1. **Single Entry Point**: Everything accessible through port 80
2. **WebSocket Support**: Properly handles WebSocket upgrade
3. **Authentication**: Auth verification cached for 30 seconds
4. **CORS**: No CORS issues as everything is same origin
5. **Load Balancing**: Can add multiple backend instances
6. **Static File Serving**: Efficient static file delivery
7. **SSL/TLS**: Easy to add HTTPS (for production)

## Troubleshooting

### Port 80 Already in Use

If port 80 is in use, you can change it in `nginx.conf`:
```nginx
server {
    listen 8080;  # Change to any available port
    ...
}
```

Then access via: `http://localhost:8080`

### Nginx Not Starting

Check if another nginx instance is running:
```bash
sudo nginx -s stop
sudo killall nginx
```

### Check Nginx Logs

```bash
sudo tail -f /var/log/nginx/error.log
```

### Permission Issues

Nginx needs root access for port 80:
```bash
sudo nginx -c $(pwd)/nginx/nginx.conf
```

## Production Considerations

For production, update `nginx.conf`:

1. **Add SSL/TLS:**
```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ...
}
```

2. **Add Rate Limiting:**
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /auth/ {
    limit_req zone=api_limit burst=20;
    ...
}
```

3. **Add Gzip Compression:**
```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

4. **Update Upstream Servers:**
```nginx
upstream auth_service {
    server auth-server-1:8000;
    server auth-server-2:8000;
}
```
