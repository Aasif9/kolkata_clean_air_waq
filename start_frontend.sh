#!/bin/bash

echo "🌍 Starting Kolkata AQI Clean Route System"
echo "=========================================="

# Check if backend is running
if ! curl -s http://localhost:5002 > /dev/null; then
    echo "❌ Backend server is not running!"
    echo "📝 Please start the backend first:"
    echo "   cd /Users/asifali/Desktop/web-projects/clean-air"
    echo "   python3 dummy_api.py"
    echo ""
    echo "⏳ Waiting for backend to start..."
    echo "   Run this script again when backend is ready."
    exit 1
fi

echo "✅ Backend server is running!"

# Start frontend server
echo "🚀 Starting frontend server..."
echo "📱 Frontend will be available at: http://localhost:8000"
echo "🔧 Backend API is running at: http://localhost:5002"
echo ""
echo "📋 Testing URLs:"
echo "   Frontend: http://localhost:8000"
echo "   Backend Status: http://localhost:5002"
echo "   AQI Stations: http://localhost:5002/stations"
echo ""
echo "🎯 Usage:"
echo "   1. Open http://localhost:8000 in your browser"
echo "   2. Click on map to set start point"
echo "   3. Click again to set end point"
echo "   4. Adjust pollution sensitivity slider"
echo "   5. Click 'Calculate Routes' to see options"
echo ""
echo "⚠️  Press Ctrl+C to stop the server"
echo "=========================================="

cd frontend
python3 -m http.server 8000
