#!/bin/bash

echo "=== Kolkata AQI Clean Route Setup ==="

echo "1. Installing dependencies..."
pip install -r requirements.txt

echo "2. Generating dummy AQI stations..."
python dummy_aqi_generator.py

echo "3. Downloading Kolkata road network (this may take a few minutes)..."
python basic_network.py

echo "4. Testing AQI interpolation..."
python dummy_aqi_interpolator.py

echo "5. Starting API server..."
echo "   Server will be available at http://localhost:5001"
echo "   Press Ctrl+C to stop the server"
python dummy_api.py
