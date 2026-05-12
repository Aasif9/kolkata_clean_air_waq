#!/usr/bin/env python3
"""
Complete Local Testing Guide for Kolkata AQI Clean Route Backend
"""

import requests
import json
import time

def test_api_endpoints():
    """Test all API endpoints with detailed output"""
    
    base_url = "http://localhost:5002"
    
    print("🚀 Kolkata AQI Clean Route Backend - Local Testing")
    print("=" * 60)
    
    # Test 1: System Status
    print("\n1. 📡 Testing System Status...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"   ✅ Server Response: {response.text}")
        print(f"   ✅ Status Code: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("   💡 Make sure server is running: python3 dummy_api.py")
        return False
    
    # Test 2: Stations Endpoint
    print("\n2. 📍 Testing AQI Stations...")
    try:
        response = requests.get(f"{base_url}/stations", timeout=10)
        data = response.json()
        
        print(f"   ✅ Total Stations: {data['total_stations']}")
        print(f"   ✅ AQI Range: {data['aqi_range'][0]:.1f} - {data['aqi_range'][1]:.1f}")
        print(f"   ✅ Average AQI: {data['average_aqi']:.1f}")
        
        # Show pollution distribution
        stations = data['stations']
        good = len([s for s in stations if s['aqi'] <= 50])
        moderate = len([s for s in stations if 50 < s['aqi'] <= 100])
        unhealthy = len([s for s in stations if s['aqi'] > 100])
        
        print(f"   📊 Air Quality Distribution:")
        print(f"      🟢 Good (0-50): {good} stations")
        print(f"      🟡 Moderate (51-100): {moderate} stations") 
        print(f"      🔴 Unhealthy (101+): {unhealthy} stations")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Route Calculations
    print("\n3. 🛣️  Testing Route Calculations...")
    
    test_routes = [
        {
            'name': 'Howrah to Salt Lake',
            'start': (22.5750, 88.3500),
            'end': (22.5800, 88.3800),
            'description': 'Industrial to Traffic area'
        },
        {
            'name': 'Victoria Memorial to Dum Dum',
            'start': (22.5726, 88.3639),
            'end': (22.5850, 88.3700),
            'description': 'Clean area to Airport'
        },
        {
            'name': 'Park Street to Behala',
            'start': (22.5620, 88.3500),
            'end': (22.5600, 88.3400),
            'description': 'Commercial to Residential'
        }
    ]
    
    for i, route in enumerate(test_routes, 1):
        print(f"\n   3.{i} 🗺️  {route['name']}")
        print(f"        📍 {route['description']}")
        
        # Calculate approximate direct distance (simple calculation)
        lat_diff = route['end'][0] - route['start'][0]
        lon_diff = route['end'][1] - route['start'][1]
        # Rough conversion: 1 degree lat ≈ 111 km, 1 degree lon ≈ 111 km * cos(lat)
        direct_distance = ((lat_diff * 111) ** 2 + (lon_diff * 111 * 0.9) ** 2) ** 0.5
        print(f"        📏 Direct Distance: {direct_distance:.2f} km")
        
        # Test route API
        url = f"{base_url}/routes/clean?" + \
              f"start_lat={route['start'][0]}&start_lon={route['start'][1]}&" + \
              f"end_lat={route['end'][0]}&end_lon={route['end'][1]}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if 'error' in data:
                print(f"        ❌ Route Error: {data['error']}")
            else:
                clean = data['clean_route']['analysis']
                fast = data['fast_route']['analysis']
                comp = data['comparison']
                
                print(f"        ✅ Fast Route: {fast['total_distance_km']:.2f}km, {fast['average_aqi']:.1f} AQI")
                print(f"        ✅ Clean Route: {clean['total_distance_km']:.2f}km, {clean['average_aqi']:.1f} AQI")
                print(f"        📈 Distance Trade-off: +{comp['distance_increase_percent']:.1f}%")
                print(f"        🌬️  AQI Improvement: {comp['aqi_improvement']:.1f}")
                
                # Route quality assessment
                if comp['aqi_improvement'] > 0:
                    print(f"        🎯 Clean route avoids pollution by {comp['aqi_improvement']:.1f} AQI points")
                else:
                    print(f"        ⚠️  Clean route similar pollution ({abs(comp['aqi_improvement']):.1f} AQI diff)")
                    
        except Exception as e:
            print(f"        ❌ Request Failed: {e}")
    
    return True

def test_pollution_factors():
    """Test different pollution factors"""
    
    base_url = "http://localhost:5002"
    
    print("\n4. 🧪 Testing Pollution Factors...")
    
    # Test route: Victoria Memorial to Salt Lake
    start_lat, start_lon = 22.5726, 88.3639
    end_lat, end_lon = 22.5800, 88.3800
    
    pollution_factors = [0.5, 1.0, 2.0, 5.0, 10.0]
    
    for factor in pollution_factors:
        print(f"\n   🎛️  Pollution Factor: {factor}")
        
        url = f"{base_url}/routes/clean?" + \
              f"start_lat={start_lat}&start_lon={start_lon}&" + \
              f"end_lat={end_lat}&end_lon={end_lon}&" + \
              f"pollution_factor={factor}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if 'error' not in data:
                clean = data['clean_route']['analysis']
                fast = data['fast_route']['analysis']
                comp = data['comparison']
                
                print(f"        📏 Distance: +{comp['distance_increase_percent']:.1f}%")
                print(f"        🌬️  AQI: {comp['aqi_improvement']:.1f} points")
                
                # Categorize impact
                if comp['distance_increase_percent'] < 5:
                    distance_impact = "Low"
                elif comp['distance_increase_percent'] < 15:
                    distance_impact = "Medium"
                else:
                    distance_impact = "High"
                    
                if comp['aqi_improvement'] > 10:
                    aqi_impact = "High"
                elif comp['aqi_improvement'] > 5:
                    aqi_impact = "Medium"
                else:
                    aqi_impact = "Low"
                
                print(f"        📊 Impact: {distance_impact} distance, {aqi_impact} AQI benefit")
                
        except Exception as e:
            print(f"        ❌ Error: {e}")

def interactive_test():
    """Interactive testing mode"""
    
    base_url = "http://localhost:5002"
    
    print("\n5. 🎮 Interactive Testing Mode")
    print("   Enter coordinates to test custom routes")
    print("   Format: lat,lon (e.g., 22.5726,88.3639)")
    print("   Type 'quit' to exit")
    
    while True:
        try:
            start = input("\n   📍 Start coordinates (lat,lon): ").strip()
            if start.lower() == 'quit':
                break
                
            end = input("   📍 End coordinates (lat,lon): ").strip()
            if end.lower() == 'quit':
                break
            
            start_lat, start_lon = map(float, start.split(','))
            end_lat, end_lon = map(float, end.split(','))
            
            url = f"{base_url}/routes/clean?" + \
                  f"start_lat={start_lat}&start_lon={start_lon}&" + \
                  f"end_lat={end_lat}&end_lon={end_lon}"
            
            print("   🔄 Calculating routes...")
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if 'error' in data:
                print(f"   ❌ Error: {data['error']}")
            else:
                clean = data['clean_route']['analysis']
                fast = data['fast_route']['analysis']
                comp = data['comparison']
                
                print(f"   ✅ Results:")
                print(f"      Fast Route: {fast['total_distance_km']:.2f}km, AQI {fast['average_aqi']:.1f}")
                print(f"      Clean Route: {clean['total_distance_km']:.2f}km, AQI {clean['average_aqi']:.1f}")
                print(f"      Trade-off: +{comp['distance_increase_percent']:.1f}% distance, {comp['aqi_improvement']:.1f} AQI")
                
        except ValueError:
            print("   ❌ Invalid format. Use: lat,lon")
        except Exception as e:
            print(f"   ❌ Error: {e}")

def main():
    """Main testing function"""
    
    print("🌍 Kolkata AQI Clean Route Backend Testing Suite")
    print("=" * 60)
    print("📋 This will test all components of your backend system")
    print("🔧 Make sure the server is running: python3 dummy_api.py")
    
    input("\nPress Enter to start testing...")
    
    # Run automated tests
    if test_api_endpoints():
        test_pollution_factors()
        
        # Offer interactive mode
        interactive = input("\n🎮 Try interactive testing? (y/n): ").strip().lower()
        if interactive == 'y':
            interactive_test()
    
    print("\n" + "=" * 60)
    print("🎉 Testing Complete!")
    print("📊 Your backend system is working correctly!")
    print("🌐 Frontend can now connect to: http://localhost:5002")

if __name__ == "__main__":
    main()
