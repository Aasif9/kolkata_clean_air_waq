from flask import Flask, jsonify, request
from flask_cors import CORS
import pickle
import os
from aqi_service import AQIInterpolator
from simple_router import SimplePollutionRouter

app = Flask(__name__)
CORS(app)

# Global variables
graph = None
interpolator = None
router = None
data_source = "real"  # Production: Always use real WAQI data

def initialize_system():
    """Initialize system with REAL WAQI AQI data"""
    global graph, interpolator, router, data_source
    
    print("Initializing Kolkata AQI Routing System with REAL WAQI data...")
    
    # Load network
    try:
        with open('kolkata_road_network.pkl', 'rb') as f:
            graph = pickle.load(f)
        print(f"Loaded network: {len(graph.nodes)} nodes")
    except FileNotFoundError:
        print("Network not found. Run basic_network.py first!")
        return False
    
    # Initialize AQI service with real WAQI data
    try:
        print("Initializing AQI service with real WAQI data...")
        interpolator = AQIInterpolator()
        
        # Show station info
        station_info = interpolator.get_station_info()
        print(f"Using {station_info['total_stations']} REAL AQI stations from WAQI")
        print(f"AQI range: {station_info['aqi_range'][0]:.1f} - {station_info['aqi_range'][1]:.1f}")
        print(f"Average AQI: {station_info['average_aqi']:.1f}")
        
    except Exception as e:
        print(f"✗ Failed to initialize AQI service: {e}")
        print("ERROR: Cannot start server without real WAQI data")
        print("Please check:")
        print("  1. WAQI token is set in waqi_token.txt or WAQI_TOKEN environment variable")
        print("  2. Internet connection is available")
        print("  3. WAQI API is accessible")
        return False
    
    # Initialize router
    router = SimplePollutionRouter(graph, interpolator)
    
    print("✓ System initialized successfully with REAL WAQI data!")
    return True
 
@app.route('/')
def home():
    return f"Kolkata AQI Routing - {data_source.upper()} Data Version"
 
@app.route('/stations')
def get_stations():
    """Get all REAL AQI stations from WAQI"""
    if not interpolator:
        return jsonify({'error': 'System not initialized'}), 500
    
    try:
        station_info = interpolator.get_station_info()
        return jsonify({
            'stations': station_info['stations'],
            'total_stations': station_info['total_stations'],
            'aqi_range': station_info['aqi_range'],
            'average_aqi': station_info['average_aqi'],
            'data_source': 'real'
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get stations: {str(e)}'}), 500

@app.route('/routes/clean')
def get_clean_route():
    """Get cleanest route between two points using REAL WAQI data"""
    try:
        start_lat = float(request.args.get('start_lat'))
        start_lon = float(request.args.get('start_lon'))
        end_lat = float(request.args.get('end_lat'))
        end_lon = float(request.args.get('end_lon'))
        pollution_factor = float(request.args.get('pollution_factor', 2.0))
        
        # Update pollution factor
        router.pollution_factor = pollution_factor
        
        # Find routes
        clean_path = router.find_cleanest_path(start_lat, start_lon, end_lat, end_lon)
        fast_path = router.find_fastest_path(start_lat, start_lon, end_lat, end_lon)
        
        if not clean_path or not fast_path:
            return jsonify({'error': 'No route found'}), 404
        
        # Convert paths to coordinates with AQI values
        def path_to_coords_with_aqi(path):
            waypoints = []
            for node in path:
                node_data = graph.nodes[node]
                lat = node_data['y']
                lon = node_data['x']
                aqi = interpolator.get_aqi_at_point(lat, lon)
                waypoints.append({
                    'lat': lat,
                    'lon': lon,
                    'aqi': aqi
                })
            return waypoints
        
        # Analyze routes
        clean_analysis = router.analyze_path_pollution(clean_path)
        fast_analysis = router.analyze_path_pollution(fast_path)
        
        # Get clean route waypoints with AQI
        clean_waypoints = path_to_coords_with_aqi(clean_path)
        
        return jsonify({
            'clean_route': {
                'waypoints': clean_waypoints,
                'node_count': len(clean_path),
                'analysis': clean_analysis
            },
            'fast_route': {
                'coordinates': [[graph.nodes[node]['y'], graph.nodes[node]['x']] for node in fast_path],
                'node_count': len(fast_path),
                'analysis': fast_analysis
            },
            'comparison': {
                'distance_increase_percent': (
                    (clean_analysis['total_distance_km'] - fast_analysis['total_distance_km']) 
                    / fast_analysis['total_distance_km'] * 100
                ),
                'aqi_improvement': (
                    fast_analysis['average_aqi'] - clean_analysis['average_aqi']
                )
            },
            'status': 'success',
            'data_source': 'real'
        })
        
    except Exception as e:
        print(f"Error calculating route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test_system():
    """Test system with sample coordinates"""
    # Test route: Howrah to Salt Lake (using real data)
    return get_clean_route()

if __name__ == '__main__':
    if initialize_system():
        print("\nStarting REAL WAQI Data API server on http://localhost:5002")
        print("=" * 60)
        print("Test endpoints:")
        print("  http://localhost:5002/")
        print("  http://localhost:5002/stations")
        print("  http://localhost:5002/test")
        print("  http://localhost:5002/routes/clean?start_lat=22.5750&start_lon=88.3500&end_lat=22.5800&end_lon=88.3800")
        print("=" * 60)
        print("✓ Using REAL WAQI AQI data only")
        print("✓ No dummy data fallback")
        print("=" * 60)
        
        app.run(debug=True, host='0.0.0.0', port=5002)
    else:
        print("\n✗ Failed to initialize system")
        print("Cannot start server without real WAQI data")
        exit(1)
