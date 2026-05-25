"""
AQI Service Layer - Production Ready
Handles real-time AQI data fetching and interpolation using WAQI API
"""
import numpy as np
from scipy.spatial.distance import cdist
import json
import os
from functools import lru_cache
from typing import List, Dict, Optional
from real_aqi_fetcher import RealAQIFetcher


class AQIService:
    """Production AQI service using real WAQI data"""
    
    def __init__(self, use_cache=True, cache_file='kolkata_real_stations.json'):
        """
        Initialize AQI service with real WAQI data
        
        Args:
            use_cache: Whether to use cached station data if available
            cache_file: Path to cache file for real stations
        """
        self.stations = []
        self.cache_file = cache_file
        self.use_cache = use_cache
        self.fetcher = RealAQIFetcher(api_type='waqi')
        self._load_stations()
    
    def _load_stations(self):
        """Load real AQI stations from WAQI API or cache"""
        print("Loading REAL WAQI AQI data...")
        
        # Try cache first if enabled
        if self.use_cache and os.path.exists(self.cache_file):
            print(f"Loading cached stations from {self.cache_file}...")
            try:
                self.stations = self.fetcher.load_stations(self.cache_file)
                if self.stations:
                    print(f"✓ Loaded {len(self.stations)} cached stations from WAQI")
                    return
            except Exception as e:
                print(f"Warning: Failed to load cache: {e}")
        
        # Fetch fresh data from WAQI API
        print("Fetching fresh stations from WAQI API...")
        try:
            self.stations = self.fetcher.fetch_stations()
            
            if not self.stations:
                raise RuntimeError("Failed to fetch stations from WAQI API")
            
            # Cache the stations for future use
            self.fetcher.save_stations(self.stations, self.cache_file)
            print(f"✓ Fetched and cached {len(self.stations)} real stations from WAQI")
            
        except Exception as e:
            print(f"✗ Error fetching WAQI data: {e}")
            raise RuntimeError(
                f"Failed to initialize AQI service with real WAQI data: {e}. "
                "Please check your WAQI token and internet connection."
            )
    
    def get_aqi_at_point(self, lat: float, lon: float, method='idw') -> float:
        """
        Get AQI at specific coordinates using interpolation
        
        Args:
            lat: Latitude
            lon: Longitude
            method: Interpolation method ('idw', 'nearest', 'weighted')
        
        Returns:
            Interpolated AQI value
        """
        if len(self.stations) < 2:
            raise RuntimeError("Insufficient stations for interpolation")
        
        if method == 'idw':
            return self._get_aqi_at_point_cached(round(lat, 5), round(lon, 5))
        elif method == 'nearest':
            return self._nearest_neighbor(lat, lon)
        else:
            return self._weighted_average(lat, lon)

    @lru_cache(maxsize=2000)
    def _get_aqi_at_point_cached(self, lat: float, lon: float) -> float:
        return self._inverse_distance_weighting(lat, lon)
    
    def _inverse_distance_weighting(self, lat: float, lon: float, power: float = 2.5, radius_km: float = 5.0) -> float:
        """Inverse Distance Weighting interpolation with radius filter and power parameter

        Args:
            lat: Latitude
            lon: Longitude
            power: Power parameter for IDW (higher = more local variation, default 2.5)
            radius_km: Radius in km to filter stations (default 5.0)

        Returns:
            Interpolated AQI value
        """
        station_coords = np.array([[s['lat'], s['lon']] for s in self.stations])
        lat_distances = (station_coords[:, 0] - lat) * 111.0
        lon_distances = (station_coords[:, 1] - lon) * 111.0 * np.cos(np.radians(lat))
        distances = np.sqrt(np.square(lat_distances) + np.square(lon_distances))

        # Find very close station
        min_dist_idx = np.argmin(distances)
        if distances[min_dist_idx] < 0.001:
            return self.stations[min_dist_idx]['aqi']

        # Filter out stations with no AQI data AND within radius
        valid_indices = []
        for i, s in enumerate(self.stations):
            if s['aqi'] is not None and distances[i] <= radius_km:
                valid_indices.append(i)

        # Fallback to nearest station if no stations in radius
        if not valid_indices:
            # Find nearest station with valid AQI
            for i in np.argsort(distances):
                if self.stations[i]['aqi'] is not None:
                    return self.stations[i]['aqi']
            raise RuntimeError("No valid AQI data available")

        valid_distances = distances[valid_indices]
        # Apply power parameter: weight = 1 / (distance^power)
        valid_weights = 1 / (np.power(valid_distances + 0.1, power))
        valid_weights = valid_weights / valid_weights.sum()

        valid_aqi = np.array([self.stations[i]['aqi'] for i in valid_indices])

        interpolated_aqi = np.sum(valid_weights * valid_aqi)
        return interpolated_aqi
    
    def _nearest_neighbor(self, lat: float, lon: float) -> float:
        """Nearest neighbor interpolation"""
        point = np.array([lat, lon])
        station_coords = np.array([[s['lat'], s['lon']] for s in self.stations])
        
        distances = cdist([point], station_coords)[0]
        min_idx = np.argmin(distances)
        
        return self.stations[min_idx]['aqi']
    
    def _weighted_average(self, lat: float, lon: float, radius: float = 3.0) -> float:
        """Weighted average within radius"""
        point = np.array([lat, lon])
        station_coords = np.array([[s['lat'], s['lon']] for s in self.stations])
        
        distances = cdist([point], station_coords)[0]
        
        # Find stations within radius
        within_radius = [i for i, d in enumerate(distances) if d <= radius]
        
        if not within_radius:
            return self._nearest_neighbor(lat, lon)
        
        weights = []
        aqi_values = []
        
        for i in within_radius:
            if self.stations[i]['aqi'] is not None:
                weight = 1 / (distances[i] + 0.1)
                weights.append(weight)
                aqi_values.append(self.stations[i]['aqi'])
        
        if not weights:
            raise RuntimeError("No valid AQI data within radius")
        
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        interpolated_aqi = np.sum(weights * np.array(aqi_values))
        return interpolated_aqi
    
    def get_station_info(self) -> Dict:
        """
        Get information about loaded stations
        
        Returns:
            Dictionary with station statistics
        """
        if not self.stations:
            raise RuntimeError("No stations loaded")
        
        aqi_values = [s['aqi'] for s in self.stations if s['aqi'] is not None]
        
        if not aqi_values:
            raise RuntimeError("No valid AQI data in stations")
        
        return {
            'total_stations': len(self.stations),
            'aqi_range': [min(aqi_values), max(aqi_values)],
            'average_aqi': np.mean(aqi_values),
            'stations': self.stations,
            'data_source': 'real'
        }
    
    def refresh_stations(self):
        """Force refresh of stations from WAQI API"""
        print("Forcing refresh of WAQI stations...")
        self.use_cache = False
        self._load_stations()
        self.use_cache = True


class AQIInterpolator:
    """Backward compatible wrapper for AQIService"""
    
    def __init__(self):
        """Initialize with real AQI service"""
        self.service = AQIService()
        self.stations = self.service.stations
    
    def get_aqi_at_point(self, lat: float, lon: float, method: str = 'idw') -> float:
        """Get AQI at point (backward compatible interface)"""
        return self.service.get_aqi_at_point(lat, lon, method)
    
    def get_station_info(self) -> Dict:
        """Get station info (backward compatible interface)"""
        return self.service.get_station_info()


# Test the service
def test_aqi_service():
    """Test the AQI service with real WAQI data"""
    print("=== Testing AQI Service ===\n")
    
    try:
        service = AQIService()
        
        # Test station info
        info = service.get_station_info()
        print(f"Total stations: {info['total_stations']}")
        print(f"AQI range: {info['aqi_range']}")
        print(f"Average AQI: {info['average_aqi']:.1f}")
        print(f"Data source: {info['data_source']}")
        
        # Test interpolation
        test_points = [
            (22.5726, 88.3639, "Kolkata Center"),
            (22.5750, 88.3500, "Howrah Area"),
            (22.5800, 88.3800, "Salt Lake"),
        ]
        
        print("\n=== AQI Interpolation Test ===")
        for lat, lon, name in test_points:
            aqi = service.get_aqi_at_point(lat, lon)
            print(f"{name}: AQI {aqi:.1f} at ({lat:.4f}, {lon:.4f})")
        
        print("\n✓ AQI Service test passed!")
        return service
        
    except Exception as e:
        print(f"✗ AQI Service test failed: {e}")
        raise


if __name__ == "__main__":
    test_aqi_service()
