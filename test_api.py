"""Test API endpoints"""
import requests
import json

base_url = "http://localhost:5002"

print("Testing API endpoints...")

# Test 1: Root endpoint
try:
    response = requests.get(f"{base_url}/", timeout=5)
    print(f"✓ Root endpoint: {response.status_code} - {response.text}")
except Exception as e:
    print(f"✗ Root endpoint failed: {e}")
    exit(1)

# Test 2: Stations endpoint
try:
    response = requests.get(f"{base_url}/stations", timeout=5)
    data = response.json()
    print(f"✓ Stations endpoint: {response.status_code}")
    print(f"  - Total stations: {data['total_stations']}")
    print(f"  - AQI range: {data['aqi_range']}")
    print(f"  - Average AQI: {data['average_aqi']:.1f}")
    print(f"  - Data source: {data['data_source']}")
except Exception as e:
    print(f"✗ Stations endpoint failed: {e}")
    exit(1)

# Test 3: Clean route endpoint
try:
    params = {
        'start_lat': 22.5750,
        'start_lon': 88.3500,
        'end_lat': 22.5800,
        'end_lon': 88.3800,
        'pollution_factor': 2.0
    }
    response = requests.get(f"{base_url}/routes/clean", params=params, timeout=10)
    data = response.json()
    print(f"✓ Clean route endpoint: {response.status_code}")
    print(f"  - Status: {data['status']}")
    print(f"  - Clean route nodes: {data['clean_route']['node_count']}")
    print(f"  - Fast route nodes: {data['fast_route']['node_count']}")
    print(f"  - AQI improvement: {data['comparison']['aqi_improvement']:.1f}")
except Exception as e:
    print(f"✗ Clean route endpoint failed: {e}")
    exit(1)

print("\n✓ All API endpoints working correctly!")
