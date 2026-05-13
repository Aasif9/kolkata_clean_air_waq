import numpy as np
import json
import math
from typing import List, Dict, Tuple
 
class DummyAQIGenerator:
    def __init__(self):
        # Kolkata center coordinates
        self.center_lat = 22.5726
        self.center_lon = 88.3639
        
        # 15km square region (7.5km in each direction from center)
        self.lat_range = 0.0675  # ~7.5km in latitude
        self.lon_range = 0.0675  # ~7.5km in longitude
        
        # Pollution hotspots (realistic Kolkata pollution sources)
        self.pollution_sources = [
            {'lat': 22.5750, 'lon': 88.3500, 'intensity': 180, 'radius': 2.0, 'name': 'Howrah Industrial'},
            {'lat': 22.5800, 'lon': 88.3800, 'intensity': 150, 'radius': 1.5, 'name': 'Salt Lake Traffic'},
            {'lat': 22.5600, 'lon': 88.3400, 'intensity': 140, 'radius': 1.8, 'name': 'Behala Residential'},
            {'lat': 22.5850, 'lon': 88.3700, 'intensity': 160, 'radius': 2.2, 'name': 'Dumdum Airport'},
            {'lat': 22.5400, 'lon': 88.3500, 'intensity': 130, 'radius': 1.5, 'name': 'Tollygunge'},
            {'lat': 22.5900, 'lon': 88.3600, 'intensity': 120, 'radius': 1.3, 'name': 'VIP Road'},
        ]
        
        # Clean areas (parks, water bodies)
        self.clean_areas = [
            {'lat': 22.5726, 'lon': 88.3639, 'intensity': 60, 'radius': 1.0, 'name': 'Victoria Memorial'},
            {'lat': 22.5650, 'lon': 88.3700, 'intensity': 70, 'radius': 0.8, 'name': 'Maidan'},
            {'lat': 22.5800, 'lon': 88.3900, 'intensity': 65, 'radius': 1.2, 'name': 'Salt Lake Central Park'},
        ]
    
    def generate_stations(self, num_stations=25, grid_type='mixed') -> List[Dict]:
        """Generate AQI stations with realistic spatial distribution"""
        
        stations = []
        
        if grid_type == 'grid':
            # Regular grid pattern
            stations = self._generate_grid_stations(num_stations)
        elif grid_type == 'random':
            # Random distribution
            stations = self._generate_random_stations(num_stations)
        else:
            # Mixed: Grid + random + strategic placement
            stations = self._generate_mixed_stations(num_stations)
        
        # Calculate AQI for each station based on pollution sources
        for station in stations:
            station['aqi'] = self._calculate_aqi_at_point(station['lat'], station['lon'])
        
        return stations
    
    def _generate_grid_stations(self, num_stations):
        """Generate stations in a regular grid"""
        stations = []
        grid_size = int(math.sqrt(num_stations))
        
        lat_step = self.lat_range * 2 / grid_size
        lon_step = self.lon_range * 2 / grid_size
        
        for i in range(grid_size):
            for j in range(grid_size):
                lat = self.center_lat - self.lat_range + (i + 0.5) * lat_step
                lon = self.center_lon - self.lon_range + (j + 0.5) * lon_step
                
                stations.append({
                    'name': f'Grid_Station_{i}_{j}',
                    'lat': lat,
                    'lon': lon,
                    'station_id': f'grid_{i}_{j}'
                })
        
        return stations[:num_stations]
    
    def _generate_random_stations(self, num_stations):
        """Generate randomly distributed stations"""
        stations = []
        
        for i in range(num_stations):
            lat = self.center_lat - self.lat_range + np.random.random() * 2 * self.lat_range
            lon = self.center_lon - self.lon_range + np.random.random() * 2 * self.lon_range
            
            stations.append({
                'name': f'Random_Station_{i}',
                'lat': lat,
                'lon': lon,
                'station_id': f'random_{i}'
            })
        
        return stations
    
    def _generate_mixed_stations(self, num_stations):
        """Generate mixed distribution: strategic + grid + random"""
        stations = []
        
        # 1. Add stations at pollution sources and clean areas
        strategic_points = self.pollution_sources + self.clean_areas
        for point in strategic_points:
            stations.append({
                'name': point['name'],
                'lat': point['lat'],
                'lon': point['lon'],
                'station_id': f'strategic_{len(stations)}'
            })
        
        # 2. Add semi-regular grid points
        remaining = num_stations - len(stations)
        grid_size = max(3, int(math.sqrt(remaining // 2)))
        
        lat_step = self.lat_range * 2 / (grid_size + 1)
        lon_step = self.lon_range * 2 / (grid_size + 1)
        
        for i in range(1, grid_size + 1):
            for j in range(1, grid_size + 1):
                if len(stations) >= num_stations:
                    break
                    
                lat = self.center_lat - self.lat_range + i * lat_step
                lon = self.center_lon - self.lon_range + j * lon_step
                
                stations.append({
                    'name': f'Mixed_Station_{i}_{j}',
                    'lat': lat,
                    'lon': lon,
                    'station_id': f'mixed_{i}_{j}'
                })
        
        # 3. Fill remaining with random points
        while len(stations) < num_stations:
            lat = self.center_lat - self.lat_range + np.random.random() * 2 * self.lat_range
            lon = self.center_lon - self.lon_range + np.random.random() * 2 * self.lon_range
            
            stations.append({
                'name': f'Random_Station_{len(stations)}',
                'lat': lat,
                'lon': lon,
                'station_id': f'random_{len(stations)}'
            })
        
        return stations[:num_stations]
    
    def _calculate_aqi_at_point(self, lat, lon):
        """Calculate realistic AQI based on pollution sources and clean areas"""
        
        # Base AQI for Kolkata (moderate pollution)
        base_aqi = 85
        
        # Add pollution from sources
        pollution_effect = 0
        for source in self.pollution_sources:
            distance = self._calculate_distance(lat, lon, source['lat'], source['lon'])
            
            if distance < source['radius']:
                # Pollution decreases with distance
                effect = source['intensity'] * (1 - distance / source['radius'])
                pollution_effect += effect
        
        # Add clean area effects
        clean_effect = 0
        for clean in self.clean_areas:
            distance = self._calculate_distance(lat, lon, clean['lat'], clean['lon'])
            
            if distance < clean['radius']:
                # Clean air effect decreases with distance
                effect = clean['intensity'] * (1 - distance / clean['radius'])
                clean_effect += effect
        
        # Combine effects
        final_aqi = base_aqi + pollution_effect - clean_effect
        
        # Add some random variation (±10)
        final_aqi += np.random.uniform(-10, 10)
        
        # Ensure realistic bounds
        final_aqi = max(30, min(300, final_aqi))
        
        return round(final_aqi, 1)
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in km"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Earth's radius in km
        km = 6371 * c
        return km
    
    def save_stations(self, stations, filename='kolkata_dummy_stations.json'):
        """Save stations to JSON file"""
        with open(filename, 'w') as f:
            json.dump(stations, f, indent=2)
        print(f"Saved {len(stations)} stations to {filename}")
    
    def load_stations(self, filename='kolkata_dummy_stations.json'):
        """Load stations from JSON file"""
        try:
            with open(filename, 'r') as f:
                stations = json.load(f)
            print(f"Loaded {len(stations)} stations from {filename}")
            return stations
        except FileNotFoundError:
            print(f"No stations file found. Generating new ones...")
            return self.generate_stations()
    
    def visualize_stations(self, stations):
        """Print station summary for visualization"""
        print(f"\n=== Kolkata Dummy AQI Stations ({len(stations)} stations) ===")
        print(f"Region: {self.center_lat - self.lat_range:.3f} to {self.center_lat + self.lat_range:.3f}°N")
        print(f"Region: {self.center_lon - self.lon_range:.3f} to {self.center_lon + self.lon_range:.3f}°E")
        print(f"Size: 15km x 15km square")
        
        # AQI distribution
        aqi_values = [s['aqi'] for s in stations]
        print(f"\nAQI Range: {min(aqi_values):.1f} - {max(aqi_values):.1f}")
        print(f"Average AQI: {np.mean(aqi_values):.1f}")
        
        # Categorize stations
        good = len([s for s in stations if s['aqi'] <= 50])
        moderate = len([s for s in stations if 50 < s['aqi'] <= 100])
        unhealthy_sensitive = len([s for s in stations if 100 < s['aqi'] <= 150])
        unhealthy = len([s for s in stations if 150 < s['aqi'] <= 200])
        very_unhealthy = len([s for s in stations if s['aqi'] > 200])
        
        print(f"\nAir Quality Distribution:")
        print(f"  Good (0-50): {good} stations")
        print(f"  Moderate (51-100): {moderate} stations")
        print(f"  Unhealthy for Sensitive (101-150): {unhealthy_sensitive} stations")
        print(f"  Unhealthy (151-200): {unhealthy} stations")
        print(f"  Very Unhealthy (201+): {very_unhealthy} stations")
        
        # Show top 5 most polluted stations
        sorted_stations = sorted(stations, key=lambda x: x['aqi'], reverse=True)
        print(f"\nTop 5 Most Polluted Stations:")
        for i, station in enumerate(sorted_stations[:5]):
            print(f"  {i+1}. {station['name']}: AQI {station['aqi']} at ({station['lat']:.4f}, {station['lon']:.4f})")
        
        # Show top 5 cleanest stations
        clean_stations = sorted(stations, key=lambda x: x['aqi'])
        print(f"\nTop 5 Cleanest Stations:")
        for i, station in enumerate(clean_stations[:5]):
            print(f"  {i+1}. {station['name']}: AQI {station['aqi']} at ({station['lat']:.4f}, {station['lon']:.4f})")
 
# Test the generator
def test_dummy_generator():
    """Test the dummy AQI generator"""
    generator = DummyAQIGenerator()
    
    # Generate 25 stations
    stations = generator.generate_stations(num_stations=25, grid_type='mixed')
    
    # Visualize
    generator.visualize_stations(stations)
    
    # Save for later use
    generator.save_stations(stations)
    
    return stations
 
if __name__ == "__main__":
    stations = test_dummy_generator()
