from flask import Flask, jsonify, request
from flask_cors import CORS
import pickle
import osmnx as ox
import os
from dummy_aqi_interpolator import DummyAQIInterpolator
from real_aqi_fetcher import RealAQIFetcher
from simple_router import SimplePollutionRouter
 
app = Flask(__name__)
CORS(app)
 
# Global variables
graph = None
interpolator = None
router = None
data_source = os.environ.get('DATA_SOURCE', 'dummy')  # 'dummy' or 'real'
 
def initialize_system():
    """Initialize system with dummy or real AQI data"""
    global graph, interpolator, router, data_source
    
    print(f"Initializing Kolkata AQI Routing System with {data_source.upper()} data...")
    
    # Load network
    try:
        with open('kolkata_road_network.pkl', 'rb') as f:
            graph = pickle.load(f)
        print(f"Loaded network: {len(graph.nodes)} nodes")
    except FileNotFoundError:
        print("Network not found. Run basic_network.py first!")
        return False
    
    # Initialize interpolator based on data source
    if data_source == 'real':
        # Use real WAQI data
        print("Fetching real AQI data from WAQI API...")
        fetcher = RealAQIFetcher(api_type='waqi')
        
        # Try to load cached real stations first
        if os.path.exists('kolkata_real_stations.json'):
            print("Loading cached real stations...")
            stations = fetcher.load_stations()
        else:
            # Fetch fresh data
            stations = fetcher.fetch_stations()
            if stations:
                fetcher.save_stations(stations)
        
        if not stations:
            print("Failed to fetch real stations. Falling back to dummy data...")
            interpolator = DummyAQIInterpolator()
            data_source = 'dummy'
        else:
            # Create interpolator with real stations
            interpolator = DummyAQIInterpolator()
            interpolator.stations = stations
            print(f"Using {len(stations)} real AQI stations from WAQI")
    else:
        # Use dummy data
        interpolator = DummyAQIInterpolator()
        
        if not interpolator.stations:
            print("No dummy stations found. Run dummy_aqi_generator.py first!")
            return False
    
    # Show station info
    station_info = interpolator.get_station_info()
    print(f"Using {station_info['total_stations']} AQI stations")
    print(f"AQI range: {station_info['aqi_range'][0]:.1f} - {station_info['aqi_range'][1]:.1f}")
    
    # Initialize router
    router = SimplePollutionRouter(graph, interpolator)
    
    print("System initialized successfully!")
    return True
 
@app.route('/')
def home():
    return f"Kolkata AQI Routing - {data_source.upper()} Data Version"
 
@app.route('/stations')
def get_stations():
    """Get all AQI stations"""
    if not interpolator:
        return jsonify({'error': 'System not initialized'}), 500
    
    station_info = interpolator.get_station_info()
    return jsonify({
        'stations': station_info['stations'],
        'total_stations': station_info['total_stations'],
        'aqi_range': station_info['aqi_range'],
        'average_aqi': station_info['average_aqi'],
        'data_source': data_source
    })
 
@app.route('/routes/clean')
def get_clean_route():
    """Get cleanest route between two points"""
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
        
        # Convert paths to coordinates
        def path_to_coords(path):
            coords = []
            for node in path:
                node_data = graph.nodes[node]
                coords.append([node_data['y'], node_data['x']])
            return coords
        
        # Analyze routes
        clean_analysis = router.analyze_path_pollution(clean_path)
        fast_analysis = router.analyze_path_pollution(fast_path)
        
        return jsonify({
            'clean_route': {
                'coordinates': path_to_coords(clean_path),
                'node_count': len(clean_path),
                'analysis': clean_analysis
            },
            'fast_route': {
                'coordinates': path_to_coords(fast_path),
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
            'data_source': data_source
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
 
@app.route('/test')
def test_system():
    """Test system with sample coordinates"""
    # Test route: Howrah to Salt Lake (using dummy data)
    return get_clean_route()
 
if __name__ == '__main__':
    if initialize_system():
        print(f"Starting {data_source.upper()} data API server on http://localhost:5002")
        print("Test endpoints:")
        print("  http://localhost:5002/")
        print("  http://localhost:5002/stations")
        print("  http://localhost:5002/test")
        print("  http://localhost:5002/routes/clean?start_lat=22.5750&start_lon=88.3500&end_lat=22.5800&end_lon=88.3800")
        print(f"\nTo use REAL WAQI data:")
        print("  1. Confirm your email: https://aqicn.org/data-platform/token-confirm/ef18ef73-d35b-4d6a-a492-0bbea7429548")
        print("  2. Get your token from the confirmation page")
        print("  3. Set WAQI_TOKEN environment variable or create waqi_token.txt")
        print("  4. Set DATA_SOURCE=real environment variable")
        print("  5. Restart the server")
        
        app.run(debug=True, host='0.0.0.0', port=5002)
    else:
        print("Failed to initialize system")
