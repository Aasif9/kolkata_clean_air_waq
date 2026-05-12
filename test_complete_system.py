import requests
import json
 
def test_complete_dummy_system():
    """Test the complete dummy AQI routing system"""
    
    base_url = "http://localhost:5002"
    
    print("=== Complete Dummy System Test ===")
    
    # Test 1: Check system status
    print("\n1. Testing system status...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # Test 2: Check stations
    print("\n2. Testing stations endpoint...")
    try:
        response = requests.get(f"{base_url}/stations")
        data = response.json()
        
        print(f"   Total stations: {data['total_stations']}")
        print(f"   AQI range: {data['aqi_range'][0]:.1f} - {data['aqi_range'][1]:.1f}")
        print(f"   Average AQI: {data['average_aqi']:.1f}")
        
        # Show sample stations
        print("   Sample stations:")
        for i, station in enumerate(data['stations'][:5]):
            print(f"     {i+1}. {station['name']}: AQI {station['aqi']} at ({station['lat']:.4f}, {station['lon']:.4f})")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Test routes
    print("\n3. Testing routing endpoints...")
    
    test_routes = [
        {
            'name': 'Howrah to Salt Lake',
            'start': (22.5750, 88.3500),
            'end': (22.5800, 88.3800)
        },
        {
            'name': 'Park Street to Dum Dum',
            'start': (22.5620, 88.3500),
            'end': (22.5850, 88.3700)
        },
        {
            'name': 'Behala to Victoria Memorial',
            'start': (22.5600, 88.3400),
            'end': (22.5726, 88.3639)
        }
    ]
    
    for route in test_routes:
        print(f"\n   Testing: {route['name']}")
        
        url = f"{base_url}/routes/clean?" + \
              f"start_lat={route['start'][0]}&start_lon={route['start'][1]}&" + \
              f"end_lat={route['end'][0]}&end_lon={route['end'][1]}"
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if 'error' in data:
                print(f"     Error: {data['error']}")
            else:
                clean = data['clean_route']
                fast = data['fast_route']
                comp = data['comparison']
                
                print(f"     Clean route: {clean['node_count']} nodes, {clean['analysis']['total_distance_km']:.2f}km")
                print(f"     Fast route: {fast['node_count']} nodes, {fast['analysis']['total_distance_km']:.2f}km")
                print(f"     AQI improvement: {comp['aqi_improvement']:.1f}")
                print(f"     Extra distance: {comp['distance_increase_percent']:.1f}%")
                print(f"     Status: {data['status']}")
                
        except Exception as e:
            print(f"     Request failed: {e}")
    
    print("\n=== Test Complete ===")
 
if __name__ == "__main__":
    test_complete_dummy_system()
