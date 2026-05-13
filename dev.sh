#!/bin/bash

trap "trap - SIGTERM && kill 0" SIGINT SIGTERM EXIT

echo "Starting backend (FastAPI)..."
cd backend && source .venv/bin/activate && python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Starting frontend (SvelteKit)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Docs:     http://localhost:8000/docs"
echo "========================================"
echo ""

wait $BACKEND_PID $FRONTEND_PID
