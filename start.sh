#!/bin/bash
set -e

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
    echo "Please edit .env to add your API keys (GEMINI_API_KEY and/or OPENAI_API_KEY)"
    echo ""
fi

# Start all services
docker-compose up --build -d

echo ""
echo "=== Taiwan Stock Analyzer ==="
echo "Frontend:  http://localhost:3000"
echo "Backend:   http://localhost:8000"
echo "Health:    http://localhost:8000/health"
echo ""
echo "Usage: Open http://localhost:3000 and enter a stock symbol (e.g., 2330)"
echo ""
echo "To stop:   docker-compose down"
echo "To logs:   docker-compose logs -f"
