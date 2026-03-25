#!/bin/bash

# Detect WSL or Native Linux
if grep -qi microsoft /proc/version; then
    echo "Running in WSL..."
    FRONTEND_PATH="/mnt/e/learn/project/FCM/Hos cap/test-frontend"
else
    echo "Running in native Linux..."
    FRONTEND_PATH="$HOME/learn/project/FCM/Hos cap/test-frontend"
fi

# Start backend
uvicorn app.main:app --reload --port 8000 &

# Start frontend
cd "$FRONTEND_PATH" || { echo "Frontend path not found"; exit 1; }
python3 -m http.server 8080 &

echo ""
echo "Backend  running on http://localhost:8000"
echo "Frontend running on http://localhost:8080"

wait