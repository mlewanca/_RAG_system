# EMERGENCY: Docker Network Killing System Network

## Immediate Recovery (if you lost SSH access)

1. **Physical/Console access required**
2. **Reboot the server** or run:
   ```bash
   sudo systemctl restart networking
   sudo systemctl restart NetworkManager
   ```

## Root Cause
Docker is creating networks that conflict with your system network configuration, causing complete network failure.

## Permanent Fix Options

### Option 1: Use Host Network Mode (Safest)
```bash
# Stop all containers
docker compose down

# Use the safe configuration
docker compose -f docker-compose-safe.yml up -d
```

This runs containers in host network mode, avoiding Docker network creation entirely.

### Option 2: Run Without Docker Compose
```bash
# Run API directly
docker run -d \
  --name rag-api \
  --network host \
  -v $(pwd)/data:/data \
  -v $(pwd)/config/.env:/app/.env:ro \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  rag_system-rag-api

# Run Redis
docker run -d \
  --name rag-redis \
  --network host \
  redis:7-alpine redis-server --bind 127.0.0.1
```

### Option 3: Check Docker Network Conflicts
```bash
# Check current networks
ip addr show
docker network ls

# Check for IP conflicts
sudo journalctl -u docker -n 100

# Check Docker daemon config
cat /etc/docker/daemon.json
```

## Possible Causes
1. **IP Range Conflict**: Docker default subnet (172.17.0.0/16) conflicts with your network
2. **Bridge Name Conflict**: Docker bridge name conflicts with existing interface
3. **iptables Rules**: Docker iptables rules breaking routing

## Prevention
1. Configure Docker daemon with custom subnet:
   ```json
   {
     "default-address-pools": [
       {"base": "10.10.0.0/16", "size": 24}
     ]
   }
   ```

2. Or use host network mode for all services

## Emergency Contacts
- If this keeps happening, the Docker daemon needs reconfiguration
- Check `/var/log/syslog` for network errors
- Consider disabling Docker's network management