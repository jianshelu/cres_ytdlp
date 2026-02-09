#!/bin/bash
set -e
fuser -k 3000/tcp || true
pkill -f "next start" || true
pkill -x next-server || true
nohup bash -lc "cd /workspace/web && npm start" > /var/log/next.log 2>&1 &
sleep 4
code=$(curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:3000 || true)
echo "3000:$code"
tail -n 12 /var/log/next.log || true
