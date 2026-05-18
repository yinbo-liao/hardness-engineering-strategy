#!/usr/bin/env bash
set -euo pipefail

echo "=== Harness Engineering — Development Setup ==="

# Backend
echo "[1/4] Setting up Python virtual environment..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Backend dependencies installed."

# Frontend
echo "[2/4] Installing frontend dependencies..."
cd ../frontend
npm install
echo "Frontend dependencies installed."

# Environment
echo "[3/4] Setting up environment..."
cd ..
if [ ! -f .env ]; then
    cp .env.example .env
    echo ".env file created from .env.example (please edit with your values)"
else
    echo ".env file already exists"
fi

# Database (requires running postgres)
echo "[4/4] Running database migrations..."
cd backend
if command -v alembic &> /dev/null; then
    alembic upgrade head
    echo "Migrations applied."
else
    echo "Skipping migrations (alembic not found on PATH)"
fi

echo ""
echo "=== Setup complete ==="
echo "Backend:  cd backend && source .venv/bin/activate && uvicorn backend.app.main:app --reload"
echo "Frontend: cd frontend && npm run dev"
echo "Docker:   docker-compose -f docker-compose.harness.yml up"
