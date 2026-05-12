import numpy as np
from scipy.spatial.distance import cdist
import json
 
class DummyAQIInterpolator:
    def __init__(self, stations_file='kolkata_dummy_stations.json'):
        self.stations = []
        self.load_stations(stations_file)
    
    def load_stations(self, filename):
        """Load stations from JSON file"""
        try:
            with open(filename, 'r') as f:
                stations_data = json.load(f)
            
            for station in stations_data:
                self.stations.append({
                    'lat': station['lat'],
                    'lon': station['lon'],
                    'aqi': station['aqi'],
                    'name': station['name']
                })
            
            print(f"Loaded {len(self.stations)} dummy AQI stations")
            
        except FileNotFoundError:
            print(f"Error: {filename} not found. Run dummy_aqi_generator.py first!")
    
    def get_aqi_at_point(self, lat, lon, method='idw'):
        """Get AQI at specific point"""
        if len(self.stations) < 2:
            return 85  # Default moderate AQI
        
        if method == 'idw':
            return self._inverse_distance_weighting(lat, lon)
        elif method == 'nearest':
            return self._nearest_neighbor(lat, lon)
        else:
            return self._weighted_average(lat, lon)
    
    def _inverse_distance_weighting(self, lat, lon, power=2):
        """IDW interpolation"""
        point = np.array([lat, lon])
        station_coords = np.array([[s['lat'], s['lon']] for s in self.stations])
        
        distances = cdist([point], station_coords)[0]
        
        # Find very close station
        min_dist_idx = np.argmin(distances)
        if distances[min_dist_idx] < 0.001:  # Very close to station
            return self.stations[min_dist_idx]['aqi']
        
        # Filter out stations with no AQI data
        valid_indices = [i for i, s in enumerate(self.stations) if s['aqi'] is not None]
        
        if not valid_indices:
            return 85
        
        valid_distances = distances[valid_indices]
        valid_weights = 1 / (valid_distances + 0.1)  # Add small value to avoid division by zero
        valid_weights = valid_weights / valid_weights.sum()
        
        valid_aqi = np.array([self.stations[i]['aqi'] for i in valid_indices])
        
        # Weighted average
        interpolated_aqi = np.sum(valid_weights * valid_aqi)
        return interpolated_aqi
    
    def _nearest_neighbor(self, lat, lon):
        """Nearest neighbor interpolation"""
        point = np.array([lat, lon])
        station_coords = np.array([[s['lat'], s['lon']] for s in self.stations])
        
        distances = cdist([point], station_coords)[0]
        min_idx = np.argmin(distances)
        
        return self.stations[min_idx]['aqi']
    
    def _weighted_average(self, lat, lon, radius=3.0):
        """Weighted average within radius"""
        point = np.array([lat, lon])
        station_coords = np.array([[s['lat'], s['lon']] for s in self.stations])
        
        distances = cdist([point], station_coords)[0]
        
        # Find stations within radius
        within_radius = [i for i, d in enumerate(distances) if d <= radius]
        
        if not within_radius:
            return self._nearest_neighbor(lat, lon)
        
        # Calculate weights (inverse distance)
        weights = []
        aqi_values = []
        
        for i in within_radius:
            if self.stations[i]['aqi'] is not None:
                weight = 1 / (distances[i] + 0.1)
                weights.append(weight)
                aqi_values.append(self.stations[i]['aqi'])
        
        if not weights:
            return 85
        
        # Normalize weights
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        # Weighted average
        interpolated_aqi = np.sum(weights * np.array(aqi_values))
        return interpolated_aqi
    
    def get_station_info(self):
        """Get information about loaded stations"""
        if not self.stations:
            return "No stations loaded"
        
        aqi_values = [s['aqi'] for s in self.stations]
        
        return {
            'total_stations': len(self.stations),
            'aqi_range': (min(aqi_values), max(aqi_values)),
            'average_aqi': np.mean(aqi_values),
            'stations': self.stations
        }
 
# Test the interpolator
def test_dummy_interpolator():
    """Test the dummy AQI interpolator"""
    interpolator = DummyAQIInterpolator()
    
    # Test interpolation at various points
    test_points = [
        (22.5726, 88.3639, "Kolkata Center"),
        (22.5750, 88.3500, "Howrah Area"),
        (22.5800, 88.3800, "Salt Lake"),
        (22.5600, 88.3400, "Behala"),
        (22.5850, 88.3700, "Dumdum"),
    ]
    
    print("\n=== AQI Interpolation Test ===")
    for lat, lon, name in test_points:
        aqi = interpolator.get_aqi_at_point(lat, lon)
        print(f"{name}: AQI {aqi:.1f} at ({lat:.4f}, {lon:.4f})")
    
    return interpolator
 
if __name__ == "__main__":
    test_dummy_interpolator()
