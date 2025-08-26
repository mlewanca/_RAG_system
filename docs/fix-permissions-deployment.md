# Deployment Steps After Permission Fix

## On your Debian server:

1. **Pull the latest changes:**
   ```bash
   cd ~/_RAG_system
   git pull origin master
   ```

2. **Fix permissions on the host:**
   ```bash
   chmod +x scripts/fix-permissions.sh
   ./scripts/fix-permissions.sh
   ```

3. **Rebuild the container with the new entrypoint:**
   ```bash
   docker compose build rag-api
   ```

4. **Start the services:**
   ```bash
   docker compose up -d
   ```

5. **Check the logs:**
   ```bash
   docker compose logs -f rag-api
   ```

## What was fixed:

1. **Docker Entrypoint**: Added a script that creates directories at container startup
2. **Graceful Fallback**: If file logging fails, the API continues with console-only logging
3. **Host Script**: Created `fix-permissions.sh` to set proper ownership (UID 1000) on host directories

## If you still see permission errors:

Run this more permissive command:
```bash
sudo chmod -R 777 ./data/logs
```

This is less secure but ensures the container can write logs.