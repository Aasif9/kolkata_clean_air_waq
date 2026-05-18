# API Data Flow and Available Data Documentation

## Overview
This document explains the complete data flow from external APIs to the frontend, including all available data points and their sources.

## 1. Primary Data Source: WAQI API

### API Information
- **Provider**: World Air Quality Index (WAQI)
- **API Endpoint**: `https://api.waqi.info/v2/map/bounds/?latlng={bounds}&token={token}`
- **Authentication**: Token-based (stored in `waqi_token.txt` or `WAQI_TOKEN` environment variable)
- **Rate Limit**: ~1000 requests/day for free tier
- **Coverage**: Global, with 100+ stations in Kolkata metropolitan area

### Code Location
**File**: `real_aqi_fetcher.py`

```python
def _fetch_waqi_bounds(self, bounds=None) -> List[Dict]:
    """Fetch stations using WAQI Map Bounds API (gets ALL stations in area)"""
    if not self.token:
        print("Error: WAQI token required")
        return []
    
    # Default bounds for Kolkata 20km radius
    if not bounds:
        bounds = "22.390,88.150,22.750,88.550"  # lat1,lon1,lat2,lon2
    
    url = f"https://api.waqi.info/v2/map/bounds/?latlng={bounds}&token={self.token}"
    
    response = requests.get(url, timeout=30)
    data = response.json()
    
    if data['status'] == 'ok':
        stations = data['data']
        return self._normalize_waqi_stations(stations)
```

### Raw WAQI API Response Structure
```json
{
  "status": "ok",
  "data": [
    {
      "idx": 1234,
      "aqi": 75,
      "station": {
        "name": "Victoria Memorial, Kolkata",
        "geo": [22.5448, 88.3426]
      },
      "iaqi": {
        "pm25": {"v": 35.5},
        "pm10": {"v": 45.2},
        "o3": {"v": 20.1},
        "no2": {"v": 15.3},
        "so2": {"v": 8.7},
        "co": {"v": 450.2}
      },
      "time": {
        "iso": "2026-05-16T12:00:00Z",
        "s": "2026-05-16 12:00:00"
      }
    }
  ]
}
```

## 2. Data Normalization

**File**: `real_aqi_fetcher.py` (lines 142-184)

```python
def _normalize_waqi_stations(self, stations: List[Dict]) -> List[Dict]:
    """Normalize WAQI station data to standard format"""
    normalized = []
    
    for station in stations:
        aqi = station.get('aqi')
        lat = station.get('lat')
        lon = station.get('lon')
        name = station.get('station', {}).get('name', 'Unknown')
        
        normalized.append({
            'name': name,
            'aqi': aqi,
            'lat': lat,
            'lon': lon,
            'station_id': f"waqi_{station.get('idx', 'unknown')}"
        })
    
    return normalized
```

### Normalized Station Data Structure
```json
{
  "name": "Victoria Memorial, Kolkata",
  "aqi": 75,
  "lat": 22.5448,
  "lon": 88.3426,
  "station_id": "waqi_1234"
}
```

## 3. AQI Interpolation

**File**: `aqi_service.py` (lines 64-112)

### Method: Inverse Distance Weighting (IDW)
```python
def _inverse_distance_weighting(self, lat: float, lon: float, power: float = 2) -> float:
    """Inverse Distance Weighting interpolation"""
    point = np.array([lat, lon])
    station_coords = np.array([[s['lat'], s['lon']] for s in self.stations])
    
    distances = cdist([point], station_coords)[0]
    
    # Filter out stations with no AQI data
    valid_indices = [i for i, s in enumerate(self.stations) if s['aqi'] is not None]
    
    valid_distances = distances[valid_indices]
    valid_weights = 1 / (valid_distances + 0.1)
    valid_weights = valid_weights / valid_weights.sum()
    
    valid_aqi = np.array([self.stations[i]['aqi'] for i in valid_indices])
    
    interpolated_aqi = np.sum(valid_weights * valid_aqi)
    return interpolated_aqi
```

**Purpose**: Estimates AQI at any point by weighting nearby stations based on distance.

## 4. Route Analysis Data Generation

**File**: `simple_router.py` (lines 93-155)

### Analysis Method
```python
def analyze_path_pollution(self, path):
    """Analyze pollution levels along a path"""
    total_distance = 0.0
    total_travel_time = 0.0
    aqi_values = []
    
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        
        # Get node coordinates
        u_data = self.graph.nodes[u]
        v_data = self.graph.nodes[v]
        
        # Calculate distance using geodesic formula
        distance = geodesic(
            (u_data['y'], u_data['x']),
            (v_data['y'], v_data['x'])
        ).kilometers
        
        # Get AQI at edge midpoint via interpolation
        mid_lat = (u_data['y'] + v_data['y']) / 2
        mid_lon = (u_data['x'] + v_data['x']) / 2
        aqi = self.aqi_interpolator.get_aqi_at_point(mid_lat, mid_lon)
        
        total_distance += distance
        total_travel_time += travel_time
        aqi_values.append(aqi)
    
    # Calculate statistics
    average_aqi = np.mean(aqi_values)
    max_aqi = np.max(aqi_values)
    min_aqi = np.min(aqi_values)
    pollution_exposure = total_distance * average_aqi
    
    return {
        'total_distance_km': total_distance,
        'total_travel_time_min': total_travel_time,
        'average_aqi': average_aqi,
        'max_aqi': max_aqi,
        'min_aqi': min_aqi,
        'pollution_exposure': pollution_exposure,
        'aqi_samples': len(aqi_values)
    }
```

## 5. Complete Data Structure

### Route Response Structure
```json
{
  "clean_route": {
    "analysis": {
      "aqi_samples": 54,
      "average_aqi": 71.42,
      "max_aqi": 72.06,
      "min_aqi": 61.0,
      "pollution_exposure": 1209.82,
      "total_distance_km": 16.94,
      "total_travel_time_min": 1466.8
    },
    "node_count": 55,
    "waypoints": [
      {
        "aqi": 71.34,
        "lat": 22.5578863,
        "lon": 88.3547306
      }
    ]
  },
  "fast_route": {
    "analysis": {
      "aqi_samples": 56,
      "average_aqi": 71.63,
      "max_aqi": 75.0,
      "min_aqi": 71.24,
      "pollution_exposure": 241.12,
      "total_distance_km": 3.37,
      "total_travel_time_min": 275.4
    },
    "node_count": 37,
    "coordinates": [
      [22.5787195, 88.3605312],
      [22.5787343, 88.3606826]
    ]
  },
  "comparison": {
    "aqi_improvement": 0.06,
    "distance_increase_percent": 13.11
  },
  "data_source": "real"
}
```

## 6. Additional Available Data (Not Currently Exposed)

### Raw WAQI Data (Available but not used)
The WAQI API provides additional pollutants that could be incorporated:

```json
{
  "iaqi": {
    "pm25": {"v": 35.5},           // PM2.5 concentration
    "pm10": {"v": 45.2},           // PM10 concentration
    "o3": {"v": 20.1},             // Ozone
    "no2": {"v": 15.3},            // Nitrogen Dioxide
    "so2": {"v": 8.7},             // Sulfur Dioxide
    "co": {"v": 450.2}             // Carbon Monoxide
  },
  "weather": {
    "temp": 32.5,                  // Temperature
    "humidity": 65,                // Humidity %
    "wind": {
      "speed": 3.2,                // Wind speed m/s
      "dir": 180                   // Wind direction degrees
    }
  },
  "time": {
    "iso": "2026-05-16T12:00:00Z", // ISO timestamp
    "s": "2026-05-16 12:00:00"     // String timestamp
  }
}
```

### Road Network Data (Available in graph)
```python
# Each node in the road network contains:
{
  'y': 22.5726,  # Latitude
  'x': 88.3639   # Longitude
}

# Each edge contains:
{
  'travel_time': 2.5,  # Travel time in minutes
  'length': 1.2        # Road length in km
}
```

## 7. Data Flow Summary

```
WAQI API (External)
    ↓
real_aqi_fetcher.py (Fetch & Normalize)
    ↓
aqi_service.py (Interpolation)
    ↓
simple_router.py (Route Calculation & Analysis)
    ↓
dummy_api.py (REST API Endpoint)
    ↓
Frontend (Display)
```

## 8. API Rate Limits & Caching

- **WAQI API**: ~1000 requests/day free tier
- **Caching Strategy**: Stations cached in `kolkata_real_stations.json`
- **Cache Duration**: Until manually refreshed or cache deleted
- **Interpolation**: No API calls needed after initial station fetch

## 9. Potential Enhancements

### Additional Data That Could Be Exposed
1. **Individual Pollutant Breakdown**: PM2.5, PM10, O3, NO2, SO2, CO
2. **Weather Data**: Temperature, humidity, wind speed/direction
3. **Temporal Data**: Historical AQI trends, time of day patterns
4. **Station Metadata**: Sensor type, data quality flags, last update time
5. **Route Segments**: AQI variations per road segment
6. **Alternative Routes**: More than 2 route options
7. **Real-time Updates**: WebSocket for live AQI changes

### Additional Analysis Metrics
1. **Health Impact Index**: Based on WHO guidelines
2. **Vulnerable Population Considerations**: Schools, hospitals nearby
3. **Time-of-Day Optimization**: Avoid high pollution during peak hours
4. **Seasonal Adjustments**: Monsoon vs dry season patterns
5. **Multi-criteria Routing**: Combine pollution, traffic, weather

## 10. Code References

- **WAQI Fetcher**: `real_aqi_fetcher.py` (lines 1-240)
- **AQI Service**: `aqi_service.py` (lines 1-239)
- **Router**: `simple_router.py` (lines 1-264)
- **API Endpoint**: `dummy_api.py` (lines 80-148)
- **Frontend Display**: `frontend/js/app.js` (lines 233-259)
