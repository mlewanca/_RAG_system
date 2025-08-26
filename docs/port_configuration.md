# Port Configuration Guide

This guide explains the port configuration for the RAG system and how to access different services.

## Default Port Configuration

The RAG system uses the following ports:

| Service | Container Port | Host Port | Description |
|---------|---------------|-----------|-------------|
| Nginx HTTP | 80 | **8880** | Web server HTTP access |
| Nginx HTTPS | 443 | **8843** | Web server HTTPS access (SSL) |
| RAG API | 8000 | 8000 | Direct API access |
| Redis | 6379 | 6379 | Cache and session storage |
| Prometheus | 9090 | 9090 | Metrics collection |
| Grafana | 3000 | 3000 | Monitoring dashboards |
| Ollama | 11434 | External | AI model server (external) |
| Open WebUI | - | 880 | Existing service (not part of RAG) |

## Why Ports 8880/8843?

We use ports 8880/8843 for nginx instead of common alternatives because:
- **Avoids conflicts** with existing services (Open WebUI on 880)
- **Pattern consistency**: 880 → 8880 (follows the Open WebUI pattern)
- **Less common** than 8080/8443, reducing conflict likelihood
- **Easy to remember** and logically grouped with other services

## Accessing the System

### Through Nginx (Recommended for Production)

Nginx provides SSL termination, rate limiting, and security headers:

```bash
# HTTP access (redirects to HTTPS)
http://localhost:8880

# HTTPS access (self-signed certificate by default)
https://localhost:8843

# API through nginx
http://localhost:8880/api
https://localhost:8843/api

# API documentation through nginx
http://localhost:8880/api/docs
https://localhost:8843/api/docs
```

### Direct API Access (Development)

For development and testing, you can access the API directly:

```bash
# Direct API access
http://localhost:8000

# API documentation
http://localhost:8000/api/docs
http://localhost:8000/api/redoc

# Health check
http://localhost:8000/health
```

## Example Usage

### Using Nginx (Production-like)

```bash
# Login through nginx
TOKEN=$(curl -k -s -X POST https://localhost:8843/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  | jq -r .access_token)

# Query through nginx
curl -k -X POST https://localhost:8843/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"How to configure the system?","max_results":5}'
```

Note: The `-k` flag is used to accept self-signed certificates. In production, use proper certificates.

### Using Direct API Access (Development)

```bash
# Login directly
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  | jq -r .access_token)

# Query directly
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"How to configure the system?","max_results":5}'
```

## Changing Port Configuration

To use different ports, update the `docker-compose.yml`:

```yaml
services:
  nginx:
    ports:
      - "YOUR_HTTP_PORT:80"
      - "YOUR_HTTPS_PORT:443"
  
  rag-api:
    ports:
      - "YOUR_API_PORT:8000"
```

## Using Standard Ports (80/443)

If you want to use standard HTTP/HTTPS ports:

1. **Stop any existing web server**:
   ```bash
   sudo systemctl stop nginx  # or apache2
   ```

2. **Update docker-compose.yml**:
   ```yaml
   nginx:
     ports:
       - "80:80"
       - "443:443"
   ```

3. **Restart the containers**:
   ```bash
   docker compose down
   docker compose up -d
   ```

## SSL/TLS Configuration

The system includes a self-signed certificate by default. For production:

1. Place your certificates in `nginx/ssl/`:
   - `cert.pem` - Your certificate
   - `key.pem` - Your private key

2. Update `nginx/nginx.conf` if using different filenames

3. Restart nginx:
   ```bash
   docker compose restart nginx
   ```

## Troubleshooting

### Port Already in Use

If you get a "port already in use" error:

```bash
# Check what's using the port
sudo lsof -i :8880  # Linux/Mac
netstat -ano | findstr :8880  # Windows

# Either stop the service or use different ports
```

### Cannot Access HTTPS

If HTTPS access fails:
- Check if SSL certificates exist in `nginx/ssl/`
- Verify nginx logs: `docker compose logs nginx`
- Try HTTP first: `http://localhost:8880`

### Connection Refused

If you get connection refused:
1. Check if containers are running: `docker compose ps`
2. Verify port mapping: `docker compose port nginx 80`
3. Check firewall rules

## Security Considerations

1. **Production Deployment**:
   - Use proper SSL certificates
   - Configure firewall rules
   - Use strong passwords

2. **Development**:
   - The current setup is suitable for local development
   - Don't expose ports to the internet without proper security

## Related Documentation

- [External Ollama Setup](external_ollama_setup.md)
- [Deployment Guide](deployment_guide.md)
- [API Documentation](api_documentation.md)