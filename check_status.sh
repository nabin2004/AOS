#!/usr/bin/env bash
set -e

echo "=== 1. System Resources ==="
uptime
free -m
echo ""

echo "=== 2. Docker Containers ==="
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "=== 3. Testing Direct Backend Port 8000 ==="
curl -i -s -m 5 http://127.0.0.1:8000/api/v1/health || echo "Direct 8000 failed"
echo ""

echo "=== 4. Testing Caddy Port 80 ==="
curl -i -s -m 5 http://127.0.0.1:80/api/v1/health || echo "Caddy 80 failed"
echo ""

echo "=== 5. aos_backend Logs (Last 30 lines) ==="
docker logs --tail 30 aos_backend || true
echo ""
