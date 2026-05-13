"""Test backend initialization without running Flask server"""
import pickle
from dummy_aqi_interpolator import DummyAQIInterpolator

print("Testing backend initialization...")

# Test 1: Load network
try:
    with open('kolkata_road_network.pkl', 'rb') as f:
        graph = pickle.load(f)
    print(f"✓ Network loaded: {len(graph.nodes)} nodes")
except FileNotFoundError:
    print("✗ Network not found: kolkata_road_network.pkl")
    exit(1)

# Test 2: Load stations
interpolator = DummyAQIInterpolator()
if not interpolator.stations:
    print("✗ No stations loaded")
    exit(1)
print(f"✓ Stations loaded: {len(interpolator.stations)} stations")

# Test 3: Get station info
station_info = interpolator.get_station_info()
print(f"✓ Station info: {station_info['total_stations']} stations, AQI range {station_info['aqi_range']}")

# Test 4: Test interpolation
test_aqi = interpolator.get_aqi_at_point(22.5726, 88.3639)
print(f"✓ Interpolation test: AQI {test_aqi:.1f} at Kolkata Center")

print("\n✓ All initialization tests passed!")
print("Backend should be able to start successfully.")
