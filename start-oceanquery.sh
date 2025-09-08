#!/bin/bash

# OceanQuery Startup Script
echo "🌊 Starting OceanQuery Project..."

# Start database
echo "📁 Starting PostgreSQL database..."
cd infra
docker-compose up postgres -d

# Wait for database to be ready
echo "⏳ Waiting for database to start..."
sleep 5

# Start backend in background
echo "🔧 Starting FastAPI backend..."
cd ../backend
source .venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Start frontend
echo "🎨 Starting Flutter frontend..."
cd ../frontend
flutter run -d web-server --web-port 3000 &
FRONTEND_PID=$!

echo ""
echo "🎉 OceanQuery is starting up!"
echo "📊 Dashboard: http://localhost:3000"
echo "🔧 API Docs: http://localhost:8000/docs"
echo "🗄️  Database: http://localhost:8081 (run: docker-compose --profile admin up)"
echo ""
echo "To stop all services, press Ctrl+C and run:"
echo "kill $BACKEND_PID $FRONTEND_PID && docker-compose -f infra/docker-compose.yml down"

# Wait for user to stop
wait
