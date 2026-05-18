import requests
import json
from typing import List, Dict, Optional

class RealAQIFetcher:
    def __init__(self, api_type='waqi', token=None):
        self.api_type = api_type
        self.token = token or self._get_token()
        
    def _get_token(self):
        """Get WAQI API token from environment or file"""
        import os
        
        # Try environment variable first
        token = os.environ.get('WAQI_TOKEN')
        if token:
            return token
        
        # Try reading from token file
        try:
            with open('waqi_token.txt', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            print("Warning: No WAQI token found. Please:")
            print("1. Set WAQI_TOKEN environment variable")
            print("2. Or create waqi_token.txt with your token")
            print("3. Get token from: https://aqicn.org/data-platform/token-confirm/YOUR_TOKEN_ID")
            return None
    
    def fetch_stations(self, bounds=None, city='Kolkata') -> List[Dict]:
        """Fetch AQI stations based on API type"""
        if self.api_type == 'waqi':
            return self._fetch_waqi_bounds(bounds)
        elif self.api_type == 'waqi_city':
            return self._fetch_waqi_city(city)
        elif self.api_type == 'cpcb':
            return self._fetch_cpcb()
        elif self.api_type == 'openaq':
            return self._fetch_openaq()
        else:
            return self._fetch_waqi_bounds(bounds)
    
    def _fetch_waqi_bounds(self, bounds=None) -> List[Dict]:
        """Fetch stations using WAQI Map Bounds API (gets ALL stations in area)"""
        if not self.token:
            print("Error: WAQI token required. Please confirm your email to get the token.")
            print("Token confirmation link: https://aqicn.org/data-platform/token-confirm/ef18ef73-d35b-4d6a-a492-0bbea7429548")
            return []
        
        # Default bounds for Kolkata 10km radius
        # Center: 22.5726, 88.3639
        # 10km ≈ 0.09 degrees
        if not bounds:
            bounds = "22.4826,88.2739,22.6626,88.4539"  # 10km radius
        
        url = f"https://api.waqi.info/v2/map/bounds/?latlng={bounds}&token={self.token}"
        
        try:
            print(f"Fetching WAQI stations with bounds: {bounds}")
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data['status'] == 'ok':
                stations = data['data']
                print(f"Found {len(stations)} stations in the area")
                return self._normalize_waqi_stations(stations)
            else:
                print(f"Error from WAQI API: {data.get('message', 'Unknown error')}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching WAQI data: {e}")
            return []
    
    def _fetch_waqi_city(self, city='Kolkata') -> List[Dict]:
        """Fetch stations using WAQI City Feed API (limited stations)"""
        if not self.token:
            print("Error: WAQI token required")
            return []
        
        url = f"https://api.waqi.info/feed/{city}/?token={self.token}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data['status'] == 'ok':
                # City feed returns single station, need to get nearby stations
                iaqi = data['data'].get('iaqi', {})
                station_data = [{
                    'name': data['data']['city']['name'],
                    'aqi': data['data']['aqi'],
                    'lat': data['data']['city']['geo'][0],
                    'lon': data['data']['city']['geo'][1],
                    'station_id': 'city_feed'
                }]
                return station_data
            else:
                print(f"Error from WAQI API: {data.get('message', 'Unknown error')}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching WAQI data: {e}")
            return []
    
    def _fetch_cpcb(self) -> List[Dict]:
        """Fetch stations from CPCB India API"""
        # CPCB API implementation
        # Note: CPCB API may require authentication
        print("CPCB API not yet implemented")
        return []
    
    def _fetch_openaq(self) -> List[Dict]:
        """Fetch stations from OpenAQ API"""
        url = "https://api.openaq.org/v2/locations?country=IN&city=Kolkata&limit=1000"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data.get('results'):
                stations = []
                for loc in data['results']:
                    # OpenAQ may not have AQI directly, need measurements
                    stations.append({
                        'name': loc.get('name', 'Unknown'),
                        'aqi': None,  # Need to fetch measurements separately
                        'lat': loc['coordinates']['latitude'],
                        'lon': loc['coordinates']['longitude'],
                        'station_id': str(loc['id'])
                    })
                print(f"Found {len(stations)} OpenAQ locations")
                return stations
            else:
                print("No results from OpenAQ")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching OpenAQ data: {e}")
            return []
    
    def _normalize_waqi_stations(self, stations: List[Dict]) -> List[Dict]:
        """Normalize WAQI station data to standard format"""
        normalized = []
        
        for station in stations:
            try:
                # WAQI Map Bounds API format
                aqi = station.get('aqi')
                lat = station.get('lat')
                lon = station.get('lon')
                name = station.get('station', {}).get('name', 'Unknown')
                
                # Skip if missing critical data
                if aqi is None or lat is None or lon is None:
                    continue
                
                # Convert AQI to float (may come as string)
                try:
                    aqi = float(aqi)
                except (ValueError, TypeError):
                    print(f"Invalid AQI value for {name}: {aqi}")
                    continue
                
                # Convert lat/lon to float
                try:
                    lat = float(lat)
                    lon = float(lon)
                except (ValueError, TypeError):
                    print(f"Invalid coordinates for {name}: {lat}, {lon}")
                    continue
                
                normalized.append({
                    'name': name,
                    'aqi': aqi,
                    'lat': lat,
                    'lon': lon,
                    'station_id': f"waqi_{station.get('idx', 'unknown')}"
                })
            except Exception as e:
                print(f"Error normalizing station: {e}")
                continue
        
        return normalized
    
    def save_stations(self, stations: List[Dict], filename='kolkata_real_stations.json'):
        """Save stations to JSON file"""
        with open(filename, 'w') as f:
            json.dump(stations, f, indent=2)
        print(f"Saved {len(stations)} stations to {filename}")
    
    def load_stations(self, filename='kolkata_real_stations.json') -> List[Dict]:
        """Load stations from JSON file"""
        try:
            with open(filename, 'r') as f:
                stations = json.load(f)
            print(f"Loaded {len(stations)} stations from {filename}")
            return stations
        except FileNotFoundError:
            print(f"No stations file found: {filename}")
            return []

def test_waqi_fetcher():
    """Test the WAQI fetcher with Map Bounds API"""
    print("=== Testing WAQI Map Bounds API ===")
    
    # Create fetcher (will look for token in environment or file)
    fetcher = RealAQIFetcher(api_type='waqi')
    
    # Fetch stations with default Kolkata bounds (20km radius)
    stations = fetcher.fetch_stations()
    
    if stations:
        print(f"\nSuccessfully fetched {len(stations)} stations")
        
        # Show statistics
        aqi_values = [s['aqi'] for s in stations if s['aqi'] is not None]
        if aqi_values:
            print(f"AQI Range: {min(aqi_values)} - {max(aqi_values)}")
            print(f"Average AQI: {sum(aqi_values)/len(aqi_values):.1f}")
        
        # Show sample stations
        print(f"\nSample stations:")
        for i, station in enumerate(stations[:10]):
            print(f"  {i+1}. {station['name']}: AQI {station['aqi']} at ({station['lat']:.4f}, {station['lon']:.4f})")
        
        if len(stations) > 10:
            print(f"  ... and {len(stations) - 10} more stations")
        
        # Save to file
        fetcher.save_stations(stations)
        
        return stations
    else:
        print("Failed to fetch stations")
        return None

if __name__ == "__main__":
    test_waqi_fetcher()
