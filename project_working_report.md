# Kolkata AQI Clean Route - Project Working Report

## Project Overview

This project is a **Pollution-Aware Routing System** for Kolkata, India that helps users find cleaner routes by avoiding high Air Quality Index (AQI) areas. The system compares the fastest route (shortest distance/time) with the cleanest route (lowest pollution exposure) and provides trade-off metrics.

### Current Status
- **Backend**: Running on http://localhost:5002 (Flask API)
- **Frontend**: Running on http://localhost:8000 (HTTP server)
- **Data Source**: Currently using DUMMY AQI data (not real-time API)
- **Coverage**: 15km x 15km region centered on Kolkata (22.5726°N, 88.3639°E)

---

## Core Algorithm: Route Finding

### 1. Road Network (basic_network.py)
The system uses **OSMnx** (OpenStreetMap) to download Kolkata's road network:
- Downloads driveable roads within the 15km x 15km region
- Creates a graph with ~31,894 nodes and edges
- Each edge has: coordinates, speed limits, and calculated travel time
- Network is cached in `kolkata_road_network.pkl` (16MB file)

### 2. Routing Algorithm (simple_router.py)

The system uses **Dijkstra's Algorithm** with custom edge weights to find routes:

#### Fastest Route
- Uses standard Dijkstra with `travel_time` as edge weight
- Minimizes total travel time
- Ignores pollution levels

#### Cleanest Route
- Uses Dijkstra with **pollution-weighted** edge weights
- For each edge, calculates a pollution penalty based on AQI at the edge midpoint
- **Weight Formula**: `travel_time * (1 + pollution_factor * (AQI / 100))`
- Default `pollution_factor = 2.0` (adjustable via API)
- Higher AQI = higher weight = algorithm avoids polluted areas

### 3. AQI Interpolation (dummy_aqi_interpolator.py)

Since AQI stations are sparse (only 25 stations), the system uses **Inverse Distance Weighting (IDW)** interpolation:
- For any point on the road network, calculates AQI based on nearby stations
- Closer stations have more influence on the AQI value
- Formula: `AQI = Σ(weight_i * AQI_i) / Σ(weight_i)` where `weight_i = 1 / distance_i^2`
- Default power = 2 (can be adjusted)

---

## How AQI Values Are Used

### 1. AQI Station Data
- 25 dummy AQI stations across Kolkata
- Each station has: latitude, longitude, AQI value, name
- AQI range: 30-300 (Good to Very Unhealthy)

### 2. Pollution Sources in Dummy Data
The dummy data includes realistic Kolkata pollution patterns:
- **Howrah Industrial**: AQI 150-180 (high pollution)
- **Salt Lake Traffic**: AQI 120-160 (moderate-high)
- **Dumdum Airport**: AQI 140-170 (high)
- **Victoria Memorial**: AQI 60-70 (clean)
- **Maidan**: AQI 65-75 (clean)

### 3. Route Analysis
For each route, the system calculates:
- **Total distance** (km)
- **Total travel time** (minutes)
- **Average AQI** along the route
- **Max/Min AQI** on the route
- **Pollution exposure** = distance × average AQI

### 4. Comparison Metrics
When comparing clean vs fast routes:
- **Distance increase**: % longer than fastest route
- **Time increase**: % longer than fastest route
- **AQI improvement**: reduction in average AQI
- **Exposure reduction**: reduction in pollution exposure

---

## Data Sources

### Current: DUMMY DATA (Default)
The system can use either dummy data or real WAQI API data.

#### Dummy Data Generation (dummy_aqi_generator.py)
1. Creates 25 AQI stations in a mixed distribution (strategic + grid + random)
2. Places stations at pollution hotspots (industrial areas, traffic zones)
3. Places stations at clean areas (parks, water bodies)
4. Calculates AQI for each station based on proximity to pollution sources
5. Adds random variation (±10) for realism
6. Saves to `kolkata_dummy_stations.json`

#### Real WAQI API Data (NEW)
The system now supports real-time AQI data from WAQI (World Air Quality Index) using the **Map Bounds API**, which retrieves ALL stations in a defined area (not just 8 official stations).

**Benefits of Real Data:**
- 30+ stations vs 25 dummy stations
- Includes official government stations (CAAQMS)
- Includes private/community sensor networks (GAIA, PurpleAir)
- Real-time AQI values
- Better coverage for accurate routing

**How to Enable Real Data:**
1. Confirm your WAQI email: https://aqicn.org/data-platform/token-confirm/ef18ef73-d35b-4d6a-a492-0bbea7429548
2. Get your API token from the confirmation page
3. Set token: `export WAQI_TOKEN="your_token"` or create `waqi_token.txt`
4. Enable real data: `export DATA_SOURCE=real`
5. Restart server: `python dummy_api.py`

**WAQI Map Bounds API Details:**
- Endpoint: `https://api.waqi.info/v2/map/bounds/?latlng={minLat,minLng,maxLat,maxLng}&token={TOKEN}`
- Kolkata Bounding Box (20km radius): `22.390,88.150,22.750,88.550`
- This covers entire Kolkata metropolitan area including Howrah, Salt Lake, Dum Dum, Behala
- Caches stations in `kolkata_real_stations.json` to minimize API calls

**See WAQI_SETUP_GUIDE.md for detailed instructions.**

---

## API Usage

### Backend API Endpoints (http://localhost:5002)

#### 1. System Status
```
GET http://localhost:5002/
```
Returns: "Kolkata AQI Routing - DUMMY Data Version" or "Kolkata AQI Routing - REAL Data Version" (depending on DATA_SOURCE)

#### 2. Get All AQI Stations
```
GET http://localhost:5002/stations
```
Returns:
```json
{
  "stations": [...],  // Array of stations with lat, lon, aqi, name
  "total_stations": 25,  // or 30+ if using real WAQI data
  "aqi_range": [30.0, 300.0],
  "average_aqi": 85.0,
  "data_source": "dummy"  // or "real"
}
```

#### 3. Get Clean vs Fast Routes
```
GET http://localhost:5002/routes/clean?start_lat=22.5750&start_lon=88.3500&end_lat=22.5800&end_lon=88.3800&pollution_factor=2.0
```

Parameters:
- `start_lat`, `start_lon`: Starting coordinates
- `end_lat`, `end_lon`: Destination coordinates
- `pollution_factor`: How much to avoid pollution (default 2.0, higher = more avoidance)

Returns:
```json
{
  "clean_route": {
    "coordinates": [[lat, lon], ...],  // Path coordinates
    "node_count": 150,
    "analysis": {
      "total_distance_km": 12.5,
      "total_travel_time_min": 25.0,
      "average_aqi": 75.0,
      "max_aqi": 120.0,
      "min_aqi": 50.0,
      "pollution_exposure": 937.5
    }
  },
  "fast_route": {
    "coordinates": [[lat, lon], ...],
    "node_count": 120,
    "analysis": {
      "total_distance_km": 10.0,
      "total_travel_time_min": 20.0,
      "average_aqi": 110.0,
      "max_aqi": 180.0,
      "min_aqi": 70.0,
      "pollution_exposure": 1100.0
    }
  },
  "comparison": {
    "distance_increase_percent": 25.0,
    "aqi_improvement": 35.0
  },
  "status": "success",
  "data_source": "dummy"
}
```

#### 4. Test Endpoint
```
GET http://localhost:5002/test
```
Returns a sample route calculation (Howrah to Salt Lake)

---

## How to Use Real API

### Option 1: WAQI Map Bounds API (RECOMMENDED - Already Implemented)
The WAQI Map Bounds API retrieves ALL stations in a defined area, including official government stations and community sensors.

**API Endpoint**:
```
https://api.waqi.info/v2/map/bounds/?latlng={minLat,minLng,maxLat,maxLng}&token={YOUR_TOKEN}
```

**Steps to Use (Already Integrated)**:
1. Confirm your email: https://aqicn.org/data-platform/token-confirm/ef18ef73-d35b-4d6a-a492-0bbea7429548
2. Get your API token from the confirmation page
3. Set token: `export WAQI_TOKEN="your_token"` or create `waqi_token.txt`
4. Enable real data: `export DATA_SOURCE=real`
5. Restart server: `python dummy_api.py`

**Implementation Details**:
- File: `real_aqi_fetcher.py` (already created)
- Bounding Box: `22.390,88.150,22.750,88.550` (20km radius around Kolkata)
- Caching: Stations cached in `kolkata_real_stations.json`
- Fallback: Automatically falls back to dummy data if API fails

**Code Example**:
```python
from real_aqi_fetcher import RealAQIFetcher

# Create fetcher
fetcher = RealAQIFetcher(api_type='waqi')

# Fetch all stations in Kolkata area
stations = fetcher.fetch_stations()
print(f"Found {len(stations)} stations")

# Save to file
fetcher.save_stations(stations)
```

### Option 2: CPCB India API (Central Pollution Control Board)
The CPCB provides real-time AQI data for Indian cities.

**API Endpoint**:
```
https://api.cpcb.gov.in/aqi_details/
```

**Steps to Integrate**:
1. Register with CPCB for API access
2. Get API key
3. Implementation in `real_aqi_fetcher.py` (placeholder exists)

### Option 3: OpenAQ API
Open-source air quality data (no API key required).

**API Endpoint**:
```
https://api.openaq.org/v2/locations?country=IN&city=Kolkata
```

**Steps to Use**:
```python
fetcher = RealAQIFetcher(api_type='openaq')
stations = fetcher.fetch_stations()
```# Clean Air Integration Diagnosis

This document provides a comprehensive analysis comparing the Green Path Server (Finland) implementation with the Kolkata AQI Clean Route project, and outlines integration strategies.

---

## Executive Summary

| Aspect | Green Path Server (Finland) | Kolkata AQI Project | Integration Feasibility |
|--------|----------------------------|---------------------|------------------------|
| **Data Source** | Raster-based (NetCDF → GeoTIFF) | Station-based (IDW interpolation) | Need adapter layer |
| **Graph Library** | igraph | NetworkX | Keep NetworkX (simpler) |
| **Road Network** | Pre-built GraphML | OSMnx download | Keep OSMnx |
| **AQI Cost Formula** | `BaseCost × (1 + AQI_coeff × sensitivity)` | `travel_time × (1 + pollution_factor × AQI/100)` | Formula compatible |
| **Multi-route** | Yes (5 sensitivities) | No (single clean route) | Can add multi-route |
| **API Framework** | Flask | Flask | Compatible |
| **Real-time Support** | Hourly/daily raster updates | Can be real-time | Stations better |

**Key Insight:** The Green Path Server's algorithm can be integrated into the Kolkata project by replacing the **data acquisition layer** (raster → stations) while keeping the **routing core** (NetworkX + Dijkstra).

---

## 1. Architecture Comparison

### 1.1 Green Path Server Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Data Acquisition                      │
│  NetCDF File → GeoTIFF Raster → Edge Sampling           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Graph Processing                       │
│  GraphML Load → Edge Cost Calculation → Dijkstra         │
│  (igraph library)                                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Route Generation                       │
│  Multiple Routes (5 sensitivities) → Exposure Analysis   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   API Layer                              │
│  Flask Endpoints → GeoJSON Response                      │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Kolkata Project Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Data Acquisition                      │
│  Dummy Stations → IDW Interpolation → Edge Assignment    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Graph Processing                       │
│  OSMnx Download → Edge Weight Calculation → Dijkstra     │
│  (NetworkX library)                                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Route Generation                       │
│  Clean Route + Fast Route → Comparison Metrics          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   API Layer                              │
│  Flask Endpoints → JSON Response                         │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Key Differences

| Component | Green Path Server | Kolkata Project | Integration Action |
|-----------|-------------------|-----------------|-------------------|
| **AQI Data** | Raster grid (continuous) | Discrete stations (25) | Keep stations, improve IDW |
| **Graph Library** | igraph (C-based, faster) | NetworkX (Python) | Keep NetworkX (simpler) |
| **Graph Storage** | GraphML (XML) | Pickle (binary) | Keep Pickle |
| **Road Network** | Pre-built, large area | Dynamic download (15km) | Keep OSMnx |
| **Cost Calculation** | Pre-computed edge attributes | On-the-fly calculation | Pre-compute for performance |
| **Route Output** | GeoJSON | JSON coordinates | Convert to GeoJSON |
| **Sensitivity** | Array of coefficients | Single pollution factor | Add multi-sensitivity |

---

## 2. Algorithm Comparison

### 2.1 AQI Cost Formulas

#### Green Path Server
```python
def get_aqi_coeff(aqi: float) -> float:
    return (aqi - 1) / 4  # Normalized AQI coefficient

def calc_aqi_cost(length: float, aqi_coeff: float, sensitivity: float) -> float:
    base_cost = length
    return round(base_cost + base_cost * aqi_coeff * sensitivity, 2)
```

**Formula:**
$$
\text{Cost} = \text{Length} \times (1 + \frac{\text{AQI} - 1}{4} \times \text{sensitivity})
$$

**AQI Range:** 1.0 - 5.0 (normalized)

#### Kolkata Project
```python
def calculate_edge_weight(travel_time: float, aqi: float, pollution_factor: float) -> float:
    return travel_time * (1 + pollution_factor * (aqi / 100))
```

**Formula:**
$$
\text{Cost} = \text{TravelTime} \times (1 + \text{pollution\_factor} \times \frac{\text{AQI}}{100})
$$

**AQI Range:** 30 - 300 (standard AQI scale)

### 2.2 Formula Conversion

To use Green Path's formula with Kolkata's AQI scale:

```python
def convert_aqi_for_green_path(aqi: float) -> float:
    """Convert standard AQI (30-300) to normalized AQI (1.0-5.0)"""
    return max(1.0, min(5.0, aqi / 60))  # 300/60 = 5.0, 30/60 = 0.5 → clamp to 1.0

def calc_aqi_cost_kolkata(
    travel_time: float, 
    aqi: float, 
    sensitivity: float
) -> float:
    """Green Path formula adapted for Kolkata AQI scale"""
    normalized_aqi = convert_aqi_for_green_path(aqi)
    aqi_coeff = (normalized_aqi - 1) / 4
    base_cost = travel_time
    return round(base_cost + base_cost * aqi_coeff * sensitivity, 2)
```

**Comparison:**
- Green Path: Uses length as base cost, normalized AQI (1-5)
- Kolkata: Uses travel time as base cost, standard AQI (30-300)
- **Both are compatible** with conversion

### 2.3 Dijkstra Implementation

#### Green Path Server (igraph)
```python
def get_least_cost_path(G, orig_node, dest_node, weight='length'):
    s_path = G.graph.get_shortest_paths(
        orig_node,
        to=dest_node,
        weights=weight,
        mode=1,
        output='epath'
    )
    return s_path[0]
```

#### Kolkata Project (NetworkX)
```python
def find_clean_route(G, start_node, end_node, pollution_factor=2.0):
    # Calculate custom weights on-the-fly
    def edge_weight(u, v, data):
        travel_time = data['travel_time']
        aqi = interpolate_aqi(G.nodes[u]['lat'], G.nodes[u]['lon'])
        return travel_time * (1 + pollution_factor * (aqi / 100))
    
    path = nx.shortest_path(G, start_node, end_node, weight=edge_weight)
    return path
```

**Integration Strategy:** Keep NetworkX but pre-compute edge weights

```python
def precompute_edge_weights(G, stations, sensitivities):
    """Pre-compute AQI costs for multiple sensitivities"""
    edge_aqi = interpolate_aqi_to_all_edges(G, stations)
    
    for edge in G.edges(data=True):
        edge_id = edge[2]['id']
        aqi = edge_aqi[edge_id]
        travel_time = edge[2]['travel_time']
        
        # Pre-compute for all sensitivities
        for sens in [0, 5, 10, 15, 20]:
            weight_name = f'clean_cost_{sens}'
            edge[2][weight_name] = calc_aqi_cost_kolkata(
                travel_time, aqi, sens
            )
    
    return G
```

---

## 3. Integration Strategy

### 3.1 Phase 1: Data Layer Adaptation

**Goal:** Replace dummy stations with real-time station data while keeping the same IDW interpolation.

#### Current Code (dummy_aqi_interpolator.py)
```python
class DummyAQIInterpolator:
    def __init__(self):
        self.stations = self._load_dummy_stations()
    
    def _load_dummy_stations(self):
        with open('kolkata_dummy_stations.json') as f:
            return json.load(f)
    
    def interpolate_aqi(self, lat, lon):
        # IDW interpolation
        weights = []
        aqi_values = []
        
        for station in self.stations:
            dist = haversine(lat, lon, station['lat'], station['lon'])
            weight = 1.0 / (dist ** 2)
            weights.append(weight)
            aqi_values.append(station['aqi'])
        
        total_weight = sum(weights)
        return sum(w * aqi for w, aqi in zip(weights, aqi_values)) / total_weight
```

#### Enhanced Code (real_aqi_interpolator.py)
```python
class RealAQIInterpolator:
    def __init__(self, api_type='waqi', update_interval_minutes=30):
        self.api_type = api_type
        self.update_interval = update_interval_minutes
        self.stations = []
        self.last_update = None
        self.fetcher = AQIFetcher(api_type)
        self._refresh_stations()
    
    def _refresh_stations(self):
        """Fetch latest station data from API"""
        self.stations = self.fetcher.fetch_stations()
        self.last_update = datetime.now()
    
    def _should_refresh(self):
        """Check if data needs refresh"""
        if self.last_update is None:
            return True
        elapsed = (datetime.now() - self.last_update).total_seconds() / 60
        return elapsed > self.update_interval
    
    def interpolate_aqi(self, lat, lon):
        """Interpolate AQI with auto-refresh"""
        if self._should_refresh():
            self._refresh_stations()
        
        # Use same IDW logic as dummy version
        weights = []
        aqi_values = []
        
        for station in self.stations:
            dist = haversine(lat, lon, station['lat'], station['lon'])
            if dist < 0.001:  # Very close to station
                return station['aqi']
            weight = 1.0 / (dist ** 2)
            weights.append(weight)
            aqi_values.append(station['aqi'])
        
        total_weight = sum(weights)
        if total_weight == 0:
            return 100.0  # Default fallback
        
        return sum(w * aqi for w, aqi in zip(weights, aqi_values)) / total_weight
    
    def get_edge_aqi_batch(self, edges):
        """Batch AQI calculation for multiple edges (optimized)"""
        edge_aqi = {}
        for edge_id, (lat, lon) in edges.items():
            edge_aqi[edge_id] = self.interpolate_aqi(lat, lon)
        return edge_aqi
```

---

### 3.2 Phase 2: API Integration

#### AQI Fetcher Implementation (aqi_fetcher.py)

```python
import requests
from abc import ABC, abstractmethod
from typing import List, Dict

class AQIFetcher(ABC):
    """Abstract base class for AQI data fetchers"""
    
    @abstractmethod
    def fetch_stations(self) -> List[Dict]:
        pass

class WAQIFetcher(AQIFetcher):
    """WAQI API implementation"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.waqi.info"
    
    def fetch_stations(self) -> List[Dict]:
        """Fetch stations within Kolkata bounding box"""
        # Kolkata bounding box
        url = f"{self.base_url}/map/bounds/?latlng=22.5,88.3,22.7,88.5&token={self.token}"
        response = requests.get(url)
        data = response.json()
        
        stations = []
        for item in data.get('data', []):
            stations.append({
                'lat': item['lat'],
                'lon': item['lon'],
                'aqi': item['aqi'],
                'name': item.get('station', {}).get('name', 'Unknown'),
                'timestamp': item.get('time', {}).get('iso')
            })
        
        return stations

class OpenAQFetcher(AQIFetcher):
    """OpenAQ API implementation"""
    
    def __init__(self):
        self.base_url = "https://api.openaq.org/v2"
    
    def fetch_stations(self) -> List[Dict]:
        """Fetch Kolkata stations from OpenAQ"""
        url = f"{self.base_url}/locations?country=IN&city=Kolkata&limit=100"
        response = requests.get(url)
        data = response.json()
        
        stations = []
        for item in data.get('results', []):
            # Get latest measurement
            measurements_url = f"{self.base_url}/measurements?location_id={item['id']}&limit=1"
            meas_response = requests.get(measurements_url)
            meas_data = meas_response.json()
            
            if meas_data.get('results'):
                latest = meas_data['results'][0]
                stations.append({
                    'lat': item['coordinates']['latitude'],
                    'lon': item['coordinates']['longitude'],
                    'aqi': latest['value'],
                    'name': item['name'],
                    'timestamp': latest['date']['utc']
                })
        
        return stations

class CPCBFetcher(AQIFetcher):
    """CPCB India API implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cpcb.gov.in"
    
    def fetch_stations(self) -> List[Dict]:
        """Fetch CPCB stations"""
        url = f"{self.base_url}/aqi_details/"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        stations = []
        # Parse CPCB response format
        for item in data.get('stations', []):
            if item.get('city', '').lower() == 'kolkata':
                stations.append({
                    'lat': item['latitude'],
                    'lon': item['longitude'],
                    'aqi': item['aqi'],
                    'name': item['station_name'],
                    'timestamp': item['timestamp']
                })
        
        return stations

class AQIFetcherFactory:
    """Factory for creating AQI fetchers"""
    
    @staticmethod
    def create(api_type: str, **kwargs) -> AQIFetcher:
        if api_type == 'waqi':
            return WAQIFetcher(token=kwargs.get('token'))
        elif api_type == 'openaq':
            return OpenAQFetcher()
        elif api_type == 'cpcb':
            return CPCBFetcher(api_key=kwargs.get('api_key'))
        else:
            raise ValueError(f"Unknown API type: {api_type}")
```

---

### 3.3 Phase 3: Graph Enhancement

#### Pre-compute Edge Costs (enhanced_network.py)

```python
import networkx as nx
import numpy as np
from typing import Dict, List

class EnhancedGraphProcessor:
    """Enhanced graph processing with pre-computed costs"""
    
    def __init__(self, graph: nx.Graph, interpolator):
        self.G = graph
        self.interpolator = interpolator
        self.sensitivities = [0, 5, 10, 15, 20]  # Green Path style
    
    def precompute_edge_costs(self):
        """Pre-compute AQI costs for all edges and sensitivities"""
        print("Pre-computing edge AQI values...")
        
        # Get all edge center points
        edge_centers = {}
        for u, v, data in self.G.edges(data=True):
            if 'geometry' in data:
                # Use geometry if available
                center = data['geometry'].interpolate(0.5, normalized=True)
                lat, lon = center.y, center.x
            else:
                # Use node coordinates
                lat = (self.G.nodes[u]['y'] + self.G.nodes[v]['y']) / 2
                lon = (self.G.nodes[u]['x'] + self.G.nodes[v]['x']) / 2
            
            edge_id = data.get('id', f"{u}-{v}")
            edge_centers[edge_id] = (lat, lon)
        
        # Batch interpolate AQI for all edges
        edge_aqi = self.interpolator.get_edge_aqi_batch(edge_centers)
        
        # Pre-compute costs for all sensitivities
        print("Computing edge costs for all sensitivities...")
        for u, v, data in self.G.edges(data=True):
            edge_id = data.get('id', f"{u}-{v}")
            aqi = edge_aqi[edge_id]
            travel_time = data.get('travel_time', data['length'] / data['speed_kmh'] * 60)
            
            # Compute costs for all sensitivities
            for sens in self.sensitivities:
                cost_attr = f'clean_cost_{sens}'
                data[cost_attr] = self._calc_aqi_cost(travel_time, aqi, sens)
        
        print("Edge cost pre-computation complete.")
        return self.G
    
    def _calc_aqi_cost(self, travel_time: float, aqi: float, sensitivity: float) -> float:
        """Calculate AQI-adjusted edge cost (Green Path formula adapted)"""
        normalized_aqi = max(1.0, min(5.0, aqi / 60))
        aqi_coeff = (normalized_aqi - 1) / 4
        base_cost = travel_time
        return round(base_cost + base_cost * aqi_coeff * sensitivity, 2)
    
    def find_clean_routes(
        self, 
        start_node: int, 
        end_node: int,
        travel_mode: str = 'drive'
    ) -> Dict[str, List[int]]:
        """Find multiple clean routes with different sensitivities"""
        routes = {}
        
        # Fastest route (sensitivity = 0)
        routes['fastest'] = nx.shortest_path(
            self.G, start_node, end_node, weight='travel_time'
        )
        
        # Clean routes with different sensitivities
        for sens in self.sensitivities[1:]:  # Skip 0 (already have fastest)
            cost_attr = f'clean_cost_{sens}'
            try:
                routes[f'clean_{sens}'] = nx.shortest_path(
                    self.G, start_node, end_node, weight=cost_attr
                )
            except nx.NetworkXNoPath:
                print(f"No path found for sensitivity {sens}")
        
        return routes
```

---

### 3.4 Phase 4: API Endpoint Enhancement

#### Enhanced API Routes (enhanced_api.py)

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import networkx as nx

app = Flask(__name__)
CORS(app)

# Initialize
interpolator = RealAQIInterpolator(api_type='waqi', update_interval_minutes=30)
G = load_graph_with_precomputed_costs(interpolator)
processor = EnhancedGraphProcessor(G, interpolator)

@app.route('/')
def index():
    return jsonify({
        "service": "Kolkata AQI Routing - Real-time Version",
        "data_source": f"real_{interpolator.api_type}",
        "last_update": interpolator.last_update.isoformat()
    })

@app.route('/stations')
def get_stations():
    """Get current AQI stations"""
    return jsonify({
        "stations": interpolator.stations,
        "total_stations": len(interpolator.stations),
        "api_type": interpolator.api_type,
        "last_update": interpolator.last_update.isoformat()
    })

@app.route('/routes/clean')
def get_clean_routes():
    """Get multiple clean routes with different sensitivities"""
    start_lat = float(request.args.get('start_lat'))
    start_lon = float(request.args.get('start_lon'))
    end_lat = float(request.args.get('end_lat'))
    end_lon = float(request.args.get('end_lon'))
    pollution_factor = float(request.args.get('pollution_factor', 2.0))
    
    # Find nearest nodes
    start_node = find_nearest_node(G, start_lat, start_lon)
    end_node = find_nearest_node(G, end_lat, end_lon)
    
    # Get routes
    routes = processor.find_clean_routes(start_node, end_node)
    
    # Analyze each route
    results = {}
    for route_type, path in routes.items():
        results[route_type] = analyze_route(G, path)
    
    # Add comparison metrics
    fastest = results['fastest']
    for route_type, route_data in results.items():
        if route_type != 'fastest':
            route_data['comparison'] = {
                'distance_increase_pct': round(
                    (route_data['total_distance_km'] - fastest['total_distance_km']) / 
                    fastest['total_distance_km'] * 100, 2
                ),
                'time_increase_pct': round(
                    (route_data['total_travel_time_min'] - fastest['total_travel_time_min']) / 
                    fastest['total_travel_time_min'] * 100, 2
                ),
                'aqi_improvement': round(
                    fastest['average_aqi'] - route_data['average_aqi'], 2
                )
            }
    
    return jsonify({
        "routes": results,
        "data_source": f"real_{interpolator.api_type}",
        "last_update": interpolator.last_update.isoformat()
    })

@app.route('/routes/clean/geojson')
def get_clean_routes_geojson():
    """Get clean routes as GeoJSON (Green Path compatible)"""
    start_lat = float(request.args.get('start_lat'))
    start_lon = float(request.args.get('start_lon'))
    end_lat = float(request.args.get('end_lat'))
    end_lon = float(request.args.get('end_lon'))
    
    start_node = find_nearest_node(G, start_lat, start_lon)
    end_node = find_nearest_node(G, end_lat, end_lon)
    
    routes = processor.find_clean_routes(start_node, end_node)
    
    features = []
    for route_type, path in routes.items():
        coords = get_path_coordinates(G, path)
        route_data = analyze_route(G, path)
        
        feature = {
            "type": "Feature",
            "properties": {
                "id": route_type,
                "type": "fastest" if route_type == "fastest" else "clean",
                "length": route_data['total_distance_km'] * 1000,
                "aqc": route_data['pollution_exposure'],
                "aqi_m": route_data['average_aqi'],
                "aqc_norm": route_data['pollution_exposure'] / (route_data['total_distance_km'] * 1000)
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat] for lat, lon in coords]
            }
        }
        features.append(feature)
    
    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })
```

---

## 4. Challenges and Solutions

### Challenge 1: Sparse Station Coverage

**Problem:** Kolkata may have only 10-20 real AQI stations, insufficient for fine-grained routing.

**Solutions:**
1. **Hybrid Approach:** Combine real stations with historical raster data
   ```python
   class HybridAQIInterpolator:
       def __init__(self, stations, raster_path):
           self.stations = stations
           self.raster = rasterio.open(raster_path)
       
       def interpolate_aqi(self, lat, lon):
           # Use real stations if nearby (< 2km)
           nearby = [s for s in self.stations 
                     if haversine(lat, lon, s['lat'], s['lon']) < 2]
           if nearby:
               return self._idw_interpolation(lat, lon, nearby)
           # Fall back to raster
           return self._sample_raster(lat, lon)
   ```

2. **Temporal Smoothing:** Use historical patterns to fill gaps
   - Store hourly AQI patterns for each location
   - Apply time-of-day adjustments to station data

3. **Mobile Sensors:** Integrate low-cost IoT sensors
   - Deploy low-cost PM2.5 sensors on public transport
   - Crowd-sourced data from mobile apps

---

### Challenge 2: Real-time Update Latency

**Problem:** API calls may be slow, affecting route calculation time.

**Solutions:**
1. **Caching with TTL:**
   ```python
   class CachedAQIFetcher:
       def __init__(self, fetcher, cache_ttl_minutes=15):
           self.fetcher = fetcher
           self.cache_ttl = cache_ttl_minutes * 60
           self.cache = {}
           self.cache_time = {}
       
       def fetch_stations(self):
           cache_key = 'stations'
           now = time.time()
           
           if cache_key in self.cache:
               if now - self.cache_time[cache_key] < self.cache_ttl:
                   return self.cache[cache_key]
           
           # Fetch fresh data
           stations = self.fetcher.fetch_stations()
           self.cache[cache_key] = stations
           self.cache_time[cache_key] = now
           return stations
   ```

2. **Background Refresh:**
   ```python
   import threading
   
   class BackgroundAQIUpdater:
       def __init__(self, interpolator, interval_minutes=30):
           self.interpolator = interpolator
           self.interval = interval_minutes * 60
           self.running = True
           self.thread = threading.Thread(target=self._update_loop)
           self.thread.start()
       
       def _update_loop(self):
           while self.running:
               self.interpolator._refresh_stations()
               time.sleep(self.interval)
   ```

3. **Edge Pre-computation:** Pre-compute edge costs and update periodically
   - Update edge costs every 15-30 minutes
   - Route calculation uses pre-computed values (instant)

---

### Challenge 3: API Rate Limits

**Problem:** Free APIs have rate limits (e.g., WAQI: 1000 requests/day).

**Solutions:**
1. **Request Batching:** Fetch all stations in one request
   ```python
   # Bad: Individual requests
   for station_id in station_ids:
       data = fetch_station(station_id)
   
   # Good: Single request
   data = fetch_all_stations_in_bbox(bbox)
   ```

2. **Multiple API Sources:** Fallback between providers
   ```python
   class MultiSourceFetcher:
       def __init__(self):
           self.fetchers = [
               WAQIFetcher(token=...),
               OpenAQFetcher(),
               CPCBFetcher(api_key=...)
           ]
       
       def fetch_stations(self):
           for fetcher in self.fetchers:
               try:
                   return fetcher.fetch_stations()
               except Exception as e:
                   print(f"{fetcher.__class__.__name__} failed: {e}")
                   continue
           raise Exception("All fetchers failed")
   ```

3. **Local Database:** Cache historical data
   ```python
   class DatabaseBackedFetcher:
       def fetch_stations(self):
           try:
               # Try API first
               fresh = self.api_fetcher.fetch_stations()
               self.db.save(fresh)
               return fresh
           except Exception:
               # Fall back to database
               return self.db.get_latest()
   ```

---

### Challenge 4: Coordinate System Differences

**Problem:** Green Path uses projected CRS (EPSG:3879), Kolkata uses WGS84 (EPSG:4326).

**Solution:** Standardize on WGS84 for Kolkata
```python
# All calculations in WGS84 (lat, lon)
# Use haversine for distances (sufficient for routing accuracy)
from geopy.distance import geodesic

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    return geodesic((lat1, lon1), (lat2, lon2)).km
```

---

### Challenge 5: Performance with Real-time Interpolation

**Problem:** IDW interpolation for every edge is slow (~50,000 edges × 25 stations).

**Solutions:**
1. **KD-Tree for Nearest Neighbors:**
   ```python
   from scipy.spatial import cKDTree
   
   class FastAQIInterpolator:
       def __init__(self, stations):
           self.stations = stations
           # Build KD-tree for fast nearest neighbor search
           coords = [[s['lat'], s['lon']] for s in stations]
           self.tree = cKDTree(coords)
           self.aqi_values = [s['aqi'] for s in stations]
       
       def interpolate_aqi(self, lat, lon):
           # Find k nearest stations (k=5)
           dists, indices = self.tree.query([lat, lon], k=5)
           
           weights = 1.0 / (dists ** 2)
           weights[weights == np.inf] = 0  # Handle exact match
           
           total_weight = np.sum(weights)
           if total_weight == 0:
               return np.mean(self.aqi_values[indices])
           
           return np.sum(weights * self.aqi_values[indices]) / total_weight
   ```

2. **Vectorized Batch Processing:**
   ```python
   def batch_interpolate_aqi(self, points):
       """Interpolate AQI for multiple points at once"""
       points_array = np.array(points)
       dists, indices = self.tree.query(points_array, k=5)
       
       # Vectorized IDW
       weights = 1.0 / (dists ** 2)
       weights[weights == np.inf] = 0
       
       total_weights = np.sum(weights, axis=1)
       weighted_aqi = np.sum(weights * self.aqi_values[indices], axis=1)
       
       return weighted_aqi / total_weights
   ```

3. **Spatial Indexing Grid:** Pre-compute AQI on a grid
   ```python
   class GridAQIInterpolator:
       def __init__(self, stations, grid_resolution=0.01):
           self.stations = stations
           self.grid = self._build_grid(grid_resolution)
       
       def _build_grid(self, resolution):
           """Pre-compute AQI grid"""
           lats = np.arange(22.5, 22.7, resolution)
           lons = np.arange(88.3, 88.5, resolution)
           grid = {}
           
           for lat in lats:
               for lon in lons:
                   grid[(lat, lon)] = self._interpolate_at_point(lat, lon)
           
           return grid
       
       def interpolate_aqi(self, lat, lon):
           """Lookup nearest grid point"""
           grid_lat = round(lat / 0.01) * 0.01
           grid_lon = round(lon / 0.01) * 0.01
           return self.grid.get((grid_lat, grid_lon), 100.0)
   ```

---

## 5. Real-Time Station Integration Guide

### Step-by-Step Implementation

#### Step 1: Choose API Provider

| Provider | Coverage | Rate Limit | Auth Required | Recommendation |
|----------|----------|------------|---------------|----------------|
| WAQI | Global | 1000/day | Token (free) | ⭐ Best for Kolkata |
| OpenAQ | Global | Unlimited | None | ⭐ Good backup |
| CPCB | India | Unknown | API Key | Good for official data |

**Recommendation:** Use WAQI as primary, OpenAQ as backup.

#### Step 2: Get API Credentials

**WAQI:**
1. Go to https://aqicn.org/api/
2. Sign up for free account
3. Get token from email

**OpenAQ:**
- No signup required
- Free and unlimited

#### Step 3: Implement Fetcher

```bash
# Create new file
touch aqi_fetcher.py
```

Add the `AQIFetcher` code from Phase 2 above.

#### Step 4: Update Configuration

```bash
# Create config file
touch config.py
```

```python
# config.py
AQI_API_TYPE = 'waqi'  # or 'openaq', 'cpcb'
AQI_API_TOKEN = 'your_waqi_token_here'  # for WAQI
AQI_UPDATE_INTERVAL_MINUTES = 30
KOLKATA_BBOX = {
    'min_lat': 22.5,
    'max_lat': 22.7,
    'min_lon': 88.3,
    'max_lon': 88.5
}
```

#### Step 5: Replace Dummy Interpolator

```bash
# Backup old file
mv dummy_aqi_interpolator.py dummy_aqi_interpolator.py.backup

# Create new file
touch real_aqi_interpolator.py
```

Add the `RealAQIInterpolator` code from Phase 1 above.

#### Step 6: Update API Server

```python
# In dummy_api.py, replace:
from dummy_aqi_interpolator import DummyAQIInterpolator

# With:
from real_aqi_interpolator import RealAQIInterpolator
from aqi_fetcher import AQIFetcherFactory

# Initialize
fetcher = AQIFetcherFactory.create(
    config.AQI_API_TYPE,
    token=config.AQI_API_TOKEN
)
interpolator = RealAQIInterpolator(
    fetcher=fetcher,
    update_interval_minutes=config.AQI_UPDATE_INTERVAL_MINUTES
)
```

#### Step 7: Add Multi-Route Support

```python
# In enhanced_api.py (new file)
from enhanced_network import EnhancedGraphProcessor

processor = EnhancedGraphProcessor(G, interpolator)

# Add new endpoint
@app.route('/routes/clean/multi')
def get_multiple_clean_routes():
    """Get multiple clean routes with different sensitivities"""
    # ... implementation from Phase 4
```

#### Step 8: Test Integration

```bash
# Start server
python dummy_api.py

# Test endpoint
curl http://localhost:5002/stations

# Should return real station data
```

---

## 6. API Compatibility

### Current API (Keep Compatible)

| Endpoint | Current Response | Enhanced Response |
|----------|------------------|-------------------|
| `GET /` | "Dummy Data Version" | "Real-time Version" |
| `GET /stations` | Dummy stations | Real stations |
| `GET /routes/clean` | Single clean route | Multiple clean routes |
| `GET /test` | Sample route | Sample route |

### New Endpoints (Add)

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /routes/clean/multi` | Multiple clean routes | Array of routes |
| `GET /routes/clean/geojson` | GeoJSON format | GeoJSON FeatureCollection |
| `GET /config` | Get current config | Config object |
| `POST /config` | Update config | Confirmation |

---

## 7. Migration Checklist

- [ ] Choose AQI API provider (WAQI recommended)
- [ ] Get API credentials
- [ ] Implement `aqi_fetcher.py`
- [ ] Implement `real_aqi_interpolator.py`
- [ ] Implement `enhanced_network.py`
- [ ] Update `dummy_api.py` to use real interpolator
- [ ] Add multi-route support
- [ ] Add GeoJSON endpoint
- [ ] Test with real data
- [ ] Update documentation
- [ ] Deploy to production

---

## 8. Performance Targets

| Metric | Current (Dummy) | Target (Real-time) |
|--------|-----------------|-------------------|
| Station fetch time | 0ms (file) | < 2s (API) |
| Route calculation | 0.5-2s | < 3s (with cache) |
| API response time | < 3s | < 5s (with real data) |
| Update frequency | Manual | Every 30 min (auto) |
| Station count | 25 (fixed) | 20-50 (dynamic) |

---

## 9. Summary

### Key Takeaways

1. **Algorithm Compatibility:** Green Path's cost formula can be adapted to Kolkata's AQI scale with simple conversion.

2. **Data Layer Only Change:** Replace the data acquisition layer (dummy → real stations) while keeping the routing core (NetworkX + Dijkstra).

3. **Keep NetworkX:** No need to switch to igraph; NetworkX is sufficient for Kolkata's scale (~32K nodes).

4. **Add Multi-Route:** Implement Green Path's multi-sensitivity approach for better user choice.

5. **Performance Optimization:** Use KD-tree, batch processing, and pre-computation to handle real-time data efficiently.

6. **API Compatibility:** Maintain existing endpoints while adding new ones for advanced features.

### Recommended Implementation Order

1. **Week 1:** Implement real AQI fetcher (WAQI)
2. **Week 2:** Replace dummy interpolator with real interpolator
3. **Week 3:** Add edge cost pre-computation
4. **Week 4:** Implement multi-route support
5. **Week 5:** Add GeoJSON endpoint
6. **Week 6:** Testing and optimization

---

**Document Version:** 1.0  
**Last Updated:** May 11, 2026


**Steps to Integrate**:
1. Sign up at https://aqicn.org/api/
2. Get free API token
3. Fetch Kolkata stations:
```python
import requests

def fetch_waqi_data():
    # Kolkata bounding box
    url = "https://api.waqi.info/map/bounds/?latlng=22.5,88.3,22.7,88.5&token=YOUR_TOKEN"
    response = requests.get(url)
    return response.json()

# Parse and convert to station format
```

### Option 3: OpenAQ API
Open-source air quality data.

**API Endpoint**:
```
https://api.openaq.org/v2/locations?country=IN&city=Kolkata
```

**Steps to Integrate**:
1. No API key required (free)
2. Fetch Kolkata stations:
```python
import requests

def fetch_openaq_data():
    url = "https://api.openaq.org/v2/locations?country=IN&city=Kolkata"
    response = requests.get(url)
    return response.json()
```

### Integration Steps (Already Completed)

The real WAQI API integration has already been implemented in the project:

1. **Created**: `real_aqi_fetcher.py` - Handles WAQI Map Bounds API calls
2. **Updated**: `dummy_api.py` - Supports both dummy and real data via DATA_SOURCE environment variable
3. **Added**: Automatic fallback to dummy data if real API fails
4. **Added**: Caching in `kolkata_real_stations.json` to minimize API calls

**To use real data, simply:**
```bash
export WAQI_TOKEN="your_token"
export DATA_SOURCE=real
python dummy_api.py
```

**To switch back to dummy data:**
```bash
export DATA_SOURCE=dummy
python dummy_api.py
```

---

## Project Structure

```
clean-air-dummy-data/
├── dummy_api.py              # Flask API server (port 5002) - supports dummy & real data
├── real_aqi_fetcher.py       # WAQI Map Bounds API fetcher (NEW)
├── simple_router.py          # Routing algorithm (Dijkstra with pollution weights)
├── dummy_aqi_generator.py    # Generates dummy AQI stations
├── dummy_aqi_interpolator.py # AQI interpolation (IDW)
├── basic_network.py          # Downloads/loads road network
├── kolkata_road_network.pkl  # Cached road network (16MB)
├── kolkata_dummy_stations.json # Cached dummy stations
├── kolkata_real_stations.json # Cached real WAQI stations (created when using real data)
├── waqi_token.txt            # WAQI API token (create this file)
├── WAQI_SETUP_GUIDE.md      # Detailed setup guide for real WAQI data (NEW)
├── requirements.txt          # Python dependencies
├── setup.sh                  # Setup script
├── start_frontend.sh         # Frontend startup script
├── frontend/                 # Frontend files
│   ├── index.html           # Main UI
│   ├── css/                 # Stylesheets
│   └── js/                  # JavaScript
└── project_working_report.md # This file
```

---

## How to Run the Project

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Setup (First Time Only)
```bash
cd /Users/asifali/clean-air-dummy-data
pip install -r requirements.txt
python dummy_aqi_generator.py  # Generate dummy stations
python basic_network.py         # Download road network (first time only)
```

### Start Backend
```bash
python dummy_api.py
```
Backend runs on http://localhost:5002

### Start Frontend
```bash
cd frontend
python3 -m http.server 8000
```
Frontend runs on http://localhost:8000

### Using the Web Interface
1. Open http://localhost:8000 in browser
2. Click on map to set start point
3. Click again to set end point
4. Adjust pollution sensitivity slider
5. Click "Calculate Routes"
6. View comparison between clean and fast routes

---

## Technical Details

### Dependencies
- **flask**: Web API framework
- **flask-cors**: CORS support
- **networkx**: Graph algorithms (Dijkstra)
- **osmnx**: OpenStreetMap integration
- **numpy**: Numerical operations
- **scipy**: Spatial distance calculations
- **geopy**: Geodesic distance calculations
- **folium**: Map visualization (if needed)

### Algorithm Complexity
- **Road Network**: ~31,894 nodes, ~50,000+ edges
- **Dijkstra Algorithm**: O(E + V log V) where V = nodes, E = edges
- **AQI Interpolation**: O(N) per point where N = number of stations (25)
- **Route Calculation**: Typically < 1 second for most routes

### Performance
- Network loading: ~5-10 seconds (from cache)
- Route calculation: ~0.5-2 seconds
- API response: < 3 seconds total

---

## Limitations and Future Improvements

### Current Limitations
1. **Dummy Data**: Not real-time AQI values
2. **Static Network**: Road network doesn't update with traffic
3. **Single Mode**: Only considers driving, not walking/cycling
4. **No Time Dimension**: AQI doesn't vary by time of day
5. **Local Only**: Works only within Kolkata region

### Future Improvements
1. **Real AQI Integration**: Connect to CPCB/WAQI/OpenAQ APIs
2. **Traffic Data**: Integrate real-time traffic data
3. **Multi-modal**: Add walking/cycling routes
4. **Temporal AQI**: Use hourly AQI forecasts
5. **User Preferences**: Allow custom pollution tolerance
6. **Mobile App**: Create React Native/mobile version
7. **Expand Region**: Cover larger area or multiple cities

---

## Conclusion

This project demonstrates a working pollution-aware routing system using:
- **Dijkstra's algorithm** with pollution-weighted edges
- **IDW interpolation** for AQI estimation between stations
- **OpenStreetMap** for realistic road networks
- **Flask API** for backend services
- **Dummy data** for reliable testing (can be replaced with real APIs)

The system successfully finds cleaner routes by avoiding high-AQI areas, providing users with trade-off metrics between speed and air quality exposure.

**To use real AQI data**, integrate with CPCB, WAQI, or OpenAQ APIs as described in the "How to Use Real API" section.










# Clean Air Integration Diagnosis

This document provides a comprehensive analysis comparing the Green Path Server (Finland) implementation with the Kolkata AQI Clean Route project, and outlines integration strategies.

---

## Executive Summary

| Aspect | Green Path Server (Finland) | Kolkata AQI Project | Integration Feasibility |
|--------|----------------------------|---------------------|------------------------|
| **Data Source** | Raster-based (NetCDF → GeoTIFF) | Station-based (IDW interpolation) | Need adapter layer |
| **Graph Library** | igraph | NetworkX | Keep NetworkX (simpler) |
| **Road Network** | Pre-built GraphML | OSMnx download | Keep OSMnx |
| **AQI Cost Formula** | `BaseCost × (1 + AQI_coeff × sensitivity)` | `travel_time × (1 + pollution_factor × AQI/100)` | Formula compatible |
| **Multi-route** | Yes (5 sensitivities) | No (single clean route) | Can add multi-route |
| **API Framework** | Flask | Flask | Compatible |
| **Real-time Support** | Hourly/daily raster updates | Can be real-time | Stations better |

**Key Insight:** The Green Path Server's algorithm can be integrated into the Kolkata project by replacing the **data acquisition layer** (raster → stations) while keeping the **routing core** (NetworkX + Dijkstra).

---

## 1. Architecture Comparison

### 1.1 Green Path Server Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Data Acquisition                      │
│  NetCDF File → GeoTIFF Raster → Edge Sampling           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Graph Processing                       │
│  GraphML Load → Edge Cost Calculation → Dijkstra         │
│  (igraph library)                                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Route Generation                       │
│  Multiple Routes (5 sensitivities) → Exposure Analysis   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   API Layer                              │
│  Flask Endpoints → GeoJSON Response                      │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Kolkata Project Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Data Acquisition                      │
│  Dummy Stations → IDW Interpolation → Edge Assignment    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Graph Processing                       │
│  OSMnx Download → Edge Weight Calculation → Dijkstra     │
│  (NetworkX library)                                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Route Generation                       │
│  Clean Route + Fast Route → Comparison Metrics          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   API Layer                              │
│  Flask Endpoints → JSON Response                         │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Key Differences

| Component | Green Path Server | Kolkata Project | Integration Action |
|-----------|-------------------|-----------------|-------------------|
| **AQI Data** | Raster grid (continuous) | Discrete stations (25) | Keep stations, improve IDW |
| **Graph Library** | igraph (C-based, faster) | NetworkX (Python) | Keep NetworkX (simpler) |
| **Graph Storage** | GraphML (XML) | Pickle (binary) | Keep Pickle |
| **Road Network** | Pre-built, large area | Dynamic download (15km) | Keep OSMnx |
| **Cost Calculation** | Pre-computed edge attributes | On-the-fly calculation | Pre-compute for performance |
| **Route Output** | GeoJSON | JSON coordinates | Convert to GeoJSON |
| **Sensitivity** | Array of coefficients | Single pollution factor | Add multi-sensitivity |

---

## 2. Algorithm Comparison

### 2.1 AQI Cost Formulas

#### Green Path Server
```python
def get_aqi_coeff(aqi: float) -> float:
    return (aqi - 1) / 4  # Normalized AQI coefficient

def calc_aqi_cost(length: float, aqi_coeff: float, sensitivity: float) -> float:
    base_cost = length
    return round(base_cost + base_cost * aqi_coeff * sensitivity, 2)
```

**Formula:**
$$
\text{Cost} = \text{Length} \times (1 + \frac{\text{AQI} - 1}{4} \times \text{sensitivity})
$$

**AQI Range:** 1.0 - 5.0 (normalized)

#### Kolkata Project
```python
def calculate_edge_weight(travel_time: float, aqi: float, pollution_factor: float) -> float:
    return travel_time * (1 + pollution_factor * (aqi / 100))
```

**Formula:**
$$
\text{Cost} = \text{TravelTime} \times (1 + \text{pollution\_factor} \times \frac{\text{AQI}}{100})
$$

**AQI Range:** 30 - 300 (standard AQI scale)

### 2.2 Formula Conversion

To use Green Path's formula with Kolkata's AQI scale:

```python
def convert_aqi_for_green_path(aqi: float) -> float:
    """Convert standard AQI (30-300) to normalized AQI (1.0-5.0)"""
    return max(1.0, min(5.0, aqi / 60))  # 300/60 = 5.0, 30/60 = 0.5 → clamp to 1.0

def calc_aqi_cost_kolkata(
    travel_time: float, 
    aqi: float, 
    sensitivity: float
) -> float:
    """Green Path formula adapted for Kolkata AQI scale"""
    normalized_aqi = convert_aqi_for_green_path(aqi)
    aqi_coeff = (normalized_aqi - 1) / 4
    base_cost = travel_time
    return round(base_cost + base_cost * aqi_coeff * sensitivity, 2)
```

**Comparison:**
- Green Path: Uses length as base cost, normalized AQI (1-5)
- Kolkata: Uses travel time as base cost, standard AQI (30-300)
- **Both are compatible** with conversion

### 2.3 Dijkstra Implementation

#### Green Path Server (igraph)
```python
def get_least_cost_path(G, orig_node, dest_node, weight='length'):
    s_path = G.graph.get_shortest_paths(
        orig_node,
        to=dest_node,
        weights=weight,
        mode=1,
        output='epath'
    )
    return s_path[0]
```

#### Kolkata Project (NetworkX)
```python
def find_clean_route(G, start_node, end_node, pollution_factor=2.0):
    # Calculate custom weights on-the-fly
    def edge_weight(u, v, data):
        travel_time = data['travel_time']
        aqi = interpolate_aqi(G.nodes[u]['lat'], G.nodes[u]['lon'])
        return travel_time * (1 + pollution_factor * (aqi / 100))
    
    path = nx.shortest_path(G, start_node, end_node, weight=edge_weight)
    return path
```

**Integration Strategy:** Keep NetworkX but pre-compute edge weights

```python
def precompute_edge_weights(G, stations, sensitivities):
    """Pre-compute AQI costs for multiple sensitivities"""
    edge_aqi = interpolate_aqi_to_all_edges(G, stations)
    
    for edge in G.edges(data=True):
        edge_id = edge[2]['id']
        aqi = edge_aqi[edge_id]
        travel_time = edge[2]['travel_time']
        
        # Pre-compute for all sensitivities
        for sens in [0, 5, 10, 15, 20]:
            weight_name = f'clean_cost_{sens}'
            edge[2][weight_name] = calc_aqi_cost_kolkata(
                travel_time, aqi, sens
            )
    
    return G
```

---

## 3. Integration Strategy

### 3.1 Phase 1: Data Layer Adaptation

**Goal:** Replace dummy stations with real-time station data while keeping the same IDW interpolation.

#### Current Code (dummy_aqi_interpolator.py)
```python
class DummyAQIInterpolator:
    def __init__(self):
        self.stations = self._load_dummy_stations()
    
    def _load_dummy_stations(self):
        with open('kolkata_dummy_stations.json') as f:
            return json.load(f)
    
    def interpolate_aqi(self, lat, lon):
        # IDW interpolation
        weights = []
        aqi_values = []
        
        for station in self.stations:
            dist = haversine(lat, lon, station['lat'], station['lon'])
            weight = 1.0 / (dist ** 2)
            weights.append(weight)
            aqi_values.append(station['aqi'])
        
        total_weight = sum(weights)
        return sum(w * aqi for w, aqi in zip(weights, aqi_values)) / total_weight
```

#### Enhanced Code (real_aqi_interpolator.py)
```python
class RealAQIInterpolator:
    def __init__(self, api_type='waqi', update_interval_minutes=30):
        self.api_type = api_type
        self.update_interval = update_interval_minutes
        self.stations = []
        self.last_update = None
        self.fetcher = AQIFetcher(api_type)
        self._refresh_stations()
    
    def _refresh_stations(self):
        """Fetch latest station data from API"""
        self.stations = self.fetcher.fetch_stations()
        self.last_update = datetime.now()
    
    def _should_refresh(self):
        """Check if data needs refresh"""
        if self.last_update is None:
            return True
        elapsed = (datetime.now() - self.last_update).total_seconds() / 60
        return elapsed > self.update_interval
    
    def interpolate_aqi(self, lat, lon):
        """Interpolate AQI with auto-refresh"""
        if self._should_refresh():
            self._refresh_stations()
        
        # Use same IDW logic as dummy version
        weights = []
        aqi_values = []
        
        for station in self.stations:
            dist = haversine(lat, lon, station['lat'], station['lon'])
            if dist < 0.001:  # Very close to station
                return station['aqi']
            weight = 1.0 / (dist ** 2)
            weights.append(weight)
            aqi_values.append(station['aqi'])
        
        total_weight = sum(weights)
        if total_weight == 0:
            return 100.0  # Default fallback
        
        return sum(w * aqi for w, aqi in zip(weights, aqi_values)) / total_weight
    
    def get_edge_aqi_batch(self, edges):
        """Batch AQI calculation for multiple edges (optimized)"""
        edge_aqi = {}
        for edge_id, (lat, lon) in edges.items():
            edge_aqi[edge_id] = self.interpolate_aqi(lat, lon)
        return edge_aqi
```

---

### 3.2 Phase 2: API Integration

#### AQI Fetcher Implementation (aqi_fetcher.py)

```python
import requests
from abc import ABC, abstractmethod
from typing import List, Dict

class AQIFetcher(ABC):
    """Abstract base class for AQI data fetchers"""
    
    @abstractmethod
    def fetch_stations(self) -> List[Dict]:
        pass

class WAQIFetcher(AQIFetcher):
    """WAQI API implementation"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.waqi.info"
    
    def fetch_stations(self) -> List[Dict]:
        """Fetch stations within Kolkata bounding box"""
        # Kolkata bounding box
        url = f"{self.base_url}/map/bounds/?latlng=22.5,88.3,22.7,88.5&token={self.token}"
        response = requests.get(url)
        data = response.json()
        
        stations = []
        for item in data.get('data', []):
            stations.append({
                'lat': item['lat'],
                'lon': item['lon'],
                'aqi': item['aqi'],
                'name': item.get('station', {}).get('name', 'Unknown'),
                'timestamp': item.get('time', {}).get('iso')
            })
        
        return stations

class OpenAQFetcher(AQIFetcher):
    """OpenAQ API implementation"""
    
    def __init__(self):
        self.base_url = "https://api.openaq.org/v2"
    
    def fetch_stations(self) -> List[Dict]:
        """Fetch Kolkata stations from OpenAQ"""
        url = f"{self.base_url}/locations?country=IN&city=Kolkata&limit=100"
        response = requests.get(url)
        data = response.json()
        
        stations = []
        for item in data.get('results', []):
            # Get latest measurement
            measurements_url = f"{self.base_url}/measurements?location_id={item['id']}&limit=1"
            meas_response = requests.get(measurements_url)
            meas_data = meas_response.json()
            
            if meas_data.get('results'):
                latest = meas_data['results'][0]
                stations.append({
                    'lat': item['coordinates']['latitude'],
                    'lon': item['coordinates']['longitude'],
                    'aqi': latest['value'],
                    'name': item['name'],
                    'timestamp': latest['date']['utc']
                })
        
        return stations

class CPCBFetcher(AQIFetcher):
    """CPCB India API implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cpcb.gov.in"
    
    def fetch_stations(self) -> List[Dict]:
        """Fetch CPCB stations"""
        url = f"{self.base_url}/aqi_details/"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        stations = []
        # Parse CPCB response format
        for item in data.get('stations', []):
            if item.get('city', '').lower() == 'kolkata':
                stations.append({
                    'lat': item['latitude'],
                    'lon': item['longitude'],
                    'aqi': item['aqi'],
                    'name': item['station_name'],
                    'timestamp': item['timestamp']
                })
        
        return stations

class AQIFetcherFactory:
    """Factory for creating AQI fetchers"""
    
    @staticmethod
    def create(api_type: str, **kwargs) -> AQIFetcher:
        if api_type == 'waqi':
            return WAQIFetcher(token=kwargs.get('token'))
        elif api_type == 'openaq':
            return OpenAQFetcher()
        elif api_type == 'cpcb':
            return CPCBFetcher(api_key=kwargs.get('api_key'))
        else:
            raise ValueError(f"Unknown API type: {api_type}")
```

---

### 3.3 Phase 3: Graph Enhancement

#### Pre-compute Edge Costs (enhanced_network.py)

```python
import networkx as nx
import numpy as np
from typing import Dict, List

class EnhancedGraphProcessor:
    """Enhanced graph processing with pre-computed costs"""
    
    def __init__(self, graph: nx.Graph, interpolator):
        self.G = graph
        self.interpolator = interpolator
        self.sensitivities = [0, 5, 10, 15, 20]  # Green Path style
    
    def precompute_edge_costs(self):
        """Pre-compute AQI costs for all edges and sensitivities"""
        print("Pre-computing edge AQI values...")
        
        # Get all edge center points
        edge_centers = {}
        for u, v, data in self.G.edges(data=True):
            if 'geometry' in data:
                # Use geometry if available
                center = data['geometry'].interpolate(0.5, normalized=True)
                lat, lon = center.y, center.x
            else:
                # Use node coordinates
                lat = (self.G.nodes[u]['y'] + self.G.nodes[v]['y']) / 2
                lon = (self.G.nodes[u]['x'] + self.G.nodes[v]['x']) / 2
            
            edge_id = data.get('id', f"{u}-{v}")
            edge_centers[edge_id] = (lat, lon)
        
        # Batch interpolate AQI for all edges
        edge_aqi = self.interpolator.get_edge_aqi_batch(edge_centers)
        
        # Pre-compute costs for all sensitivities
        print("Computing edge costs for all sensitivities...")
        for u, v, data in self.G.edges(data=True):
            edge_id = data.get('id', f"{u}-{v}")
            aqi = edge_aqi[edge_id]
            travel_time = data.get('travel_time', data['length'] / data['speed_kmh'] * 60)
            
            # Compute costs for all sensitivities
            for sens in self.sensitivities:
                cost_attr = f'clean_cost_{sens}'
                data[cost_attr] = self._calc_aqi_cost(travel_time, aqi, sens)
        
        print("Edge cost pre-computation complete.")
        return self.G
    
    def _calc_aqi_cost(self, travel_time: float, aqi: float, sensitivity: float) -> float:
        """Calculate AQI-adjusted edge cost (Green Path formula adapted)"""
        normalized_aqi = max(1.0, min(5.0, aqi / 60))
        aqi_coeff = (normalized_aqi - 1) / 4
        base_cost = travel_time
        return round(base_cost + base_cost * aqi_coeff * sensitivity, 2)
    
    def find_clean_routes(
        self, 
        start_node: int, 
        end_node: int,
        travel_mode: str = 'drive'
    ) -> Dict[str, List[int]]:
        """Find multiple clean routes with different sensitivities"""
        routes = {}
        
        # Fastest route (sensitivity = 0)
        routes['fastest'] = nx.shortest_path(
            self.G, start_node, end_node, weight='travel_time'
        )
        
        # Clean routes with different sensitivities
        for sens in self.sensitivities[1:]:  # Skip 0 (already have fastest)
            cost_attr = f'clean_cost_{sens}'
            try:
                routes[f'clean_{sens}'] = nx.shortest_path(
                    self.G, start_node, end_node, weight=cost_attr
                )
            except nx.NetworkXNoPath:
                print(f"No path found for sensitivity {sens}")
        
        return routes
```

---

### 3.4 Phase 4: API Endpoint Enhancement

#### Enhanced API Routes (enhanced_api.py)

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import networkx as nx

app = Flask(__name__)
CORS(app)

# Initialize
interpolator = RealAQIInterpolator(api_type='waqi', update_interval_minutes=30)
G = load_graph_with_precomputed_costs(interpolator)
processor = EnhancedGraphProcessor(G, interpolator)

@app.route('/')
def index():
    return jsonify({
        "service": "Kolkata AQI Routing - Real-time Version",
        "data_source": f"real_{interpolator.api_type}",
        "last_update": interpolator.last_update.isoformat()
    })

@app.route('/stations')
def get_stations():
    """Get current AQI stations"""
    return jsonify({
        "stations": interpolator.stations,
        "total_stations": len(interpolator.stations),
        "api_type": interpolator.api_type,
        "last_update": interpolator.last_update.isoformat()
    })

@app.route('/routes/clean')
def get_clean_routes():
    """Get multiple clean routes with different sensitivities"""
    start_lat = float(request.args.get('start_lat'))
    start_lon = float(request.args.get('start_lon'))
    end_lat = float(request.args.get('end_lat'))
    end_lon = float(request.args.get('end_lon'))
    pollution_factor = float(request.args.get('pollution_factor', 2.0))
    
    # Find nearest nodes
    start_node = find_nearest_node(G, start_lat, start_lon)
    end_node = find_nearest_node(G, end_lat, end_lon)
    
    # Get routes
    routes = processor.find_clean_routes(start_node, end_node)
    
    # Analyze each route
    results = {}
    for route_type, path in routes.items():
        results[route_type] = analyze_route(G, path)
    
    # Add comparison metrics
    fastest = results['fastest']
    for route_type, route_data in results.items():
        if route_type != 'fastest':
            route_data['comparison'] = {
                'distance_increase_pct': round(
                    (route_data['total_distance_km'] - fastest['total_distance_km']) / 
                    fastest['total_distance_km'] * 100, 2
                ),
                'time_increase_pct': round(
                    (route_data['total_travel_time_min'] - fastest['total_travel_time_min']) / 
                    fastest['total_travel_time_min'] * 100, 2
                ),
                'aqi_improvement': round(
                    fastest['average_aqi'] - route_data['average_aqi'], 2
                )
            }
    
    return jsonify({
        "routes": results,
        "data_source": f"real_{interpolator.api_type}",
        "last_update": interpolator.last_update.isoformat()
    })

@app.route('/routes/clean/geojson')
def get_clean_routes_geojson():
    """Get clean routes as GeoJSON (Green Path compatible)"""
    start_lat = float(request.args.get('start_lat'))
    start_lon = float(request.args.get('start_lon'))
    end_lat = float(request.args.get('end_lat'))
    end_lon = float(request.args.get('end_lon'))
    
    start_node = find_nearest_node(G, start_lat, start_lon)
    end_node = find_nearest_node(G, end_lat, end_lon)
    
    routes = processor.find_clean_routes(start_node, end_node)
    
    features = []
    for route_type, path in routes.items():
        coords = get_path_coordinates(G, path)
        route_data = analyze_route(G, path)
        
        feature = {
            "type": "Feature",
            "properties": {
                "id": route_type,
                "type": "fastest" if route_type == "fastest" else "clean",
                "length": route_data['total_distance_km'] * 1000,
                "aqc": route_data['pollution_exposure'],
                "aqi_m": route_data['average_aqi'],
                "aqc_norm": route_data['pollution_exposure'] / (route_data['total_distance_km'] * 1000)
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat] for lat, lon in coords]
            }
        }
        features.append(feature)
    
    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })
```

---

## 4. Challenges and Solutions

### Challenge 1: Sparse Station Coverage

**Problem:** Kolkata may have only 10-20 real AQI stations, insufficient for fine-grained routing.

**Solutions:**
1. **Hybrid Approach:** Combine real stations with historical raster data
   ```python
   class HybridAQIInterpolator:
       def __init__(self, stations, raster_path):
           self.stations = stations
           self.raster = rasterio.open(raster_path)
       
       def interpolate_aqi(self, lat, lon):
           # Use real stations if nearby (< 2km)
           nearby = [s for s in self.stations 
                     if haversine(lat, lon, s['lat'], s['lon']) < 2]
           if nearby:
               return self._idw_interpolation(lat, lon, nearby)
           # Fall back to raster
           return self._sample_raster(lat, lon)
   ```

2. **Temporal Smoothing:** Use historical patterns to fill gaps
   - Store hourly AQI patterns for each location
   - Apply time-of-day adjustments to station data

3. **Mobile Sensors:** Integrate low-cost IoT sensors
   - Deploy low-cost PM2.5 sensors on public transport
   - Crowd-sourced data from mobile apps

---

### Challenge 2: Real-time Update Latency

**Problem:** API calls may be slow, affecting route calculation time.

**Solutions:**
1. **Caching with TTL:**
   ```python
   class CachedAQIFetcher:
       def __init__(self, fetcher, cache_ttl_minutes=15):
           self.fetcher = fetcher
           self.cache_ttl = cache_ttl_minutes * 60
           self.cache = {}
           self.cache_time = {}
       
       def fetch_stations(self):
           cache_key = 'stations'
           now = time.time()
           
           if cache_key in self.cache:
               if now - self.cache_time[cache_key] < self.cache_ttl:
                   return self.cache[cache_key]
           
           # Fetch fresh data
           stations = self.fetcher.fetch_stations()
           self.cache[cache_key] = stations
           self.cache_time[cache_key] = now
           return stations
   ```

2. **Background Refresh:**
   ```python
   import threading
   
   class BackgroundAQIUpdater:
       def __init__(self, interpolator, interval_minutes=30):
           self.interpolator = interpolator
           self.interval = interval_minutes * 60
           self.running = True
           self.thread = threading.Thread(target=self._update_loop)
           self.thread.start()
       
       def _update_loop(self):
           while self.running:
               self.interpolator._refresh_stations()
               time.sleep(self.interval)
   ```

3. **Edge Pre-computation:** Pre-compute edge costs and update periodically
   - Update edge costs every 15-30 minutes
   - Route calculation uses pre-computed values (instant)

---

### Challenge 3: API Rate Limits

**Problem:** Free APIs have rate limits (e.g., WAQI: 1000 requests/day).

**Solutions:**
1. **Request Batching:** Fetch all stations in one request
   ```python
   # Bad: Individual requests
   for station_id in station_ids:
       data = fetch_station(station_id)
   
   # Good: Single request
   data = fetch_all_stations_in_bbox(bbox)
   ```

2. **Multiple API Sources:** Fallback between providers
   ```python
   class MultiSourceFetcher:
       def __init__(self):
           self.fetchers = [
               WAQIFetcher(token=...),
               OpenAQFetcher(),
               CPCBFetcher(api_key=...)
           ]
       
       def fetch_stations(self):
           for fetcher in self.fetchers:
               try:
                   return fetcher.fetch_stations()
               except Exception as e:
                   print(f"{fetcher.__class__.__name__} failed: {e}")
                   continue
           raise Exception("All fetchers failed")
   ```

3. **Local Database:** Cache historical data
   ```python
   class DatabaseBackedFetcher:
       def fetch_stations(self):
           try:
               # Try API first
               fresh = self.api_fetcher.fetch_stations()
               self.db.save(fresh)
               return fresh
           except Exception:
               # Fall back to database
               return self.db.get_latest()
   ```

---

### Challenge 4: Coordinate System Differences

**Problem:** Green Path uses projected CRS (EPSG:3879), Kolkata uses WGS84 (EPSG:4326).

**Solution:** Standardize on WGS84 for Kolkata
```python
# All calculations in WGS84 (lat, lon)
# Use haversine for distances (sufficient for routing accuracy)
from geopy.distance import geodesic

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    return geodesic((lat1, lon1), (lat2, lon2)).km
```

---

### Challenge 5: Performance with Real-time Interpolation

**Problem:** IDW interpolation for every edge is slow (~50,000 edges × 25 stations).

**Solutions:**
1. **KD-Tree for Nearest Neighbors:**
   ```python
   from scipy.spatial import cKDTree
   
   class FastAQIInterpolator:
       def __init__(self, stations):
           self.stations = stations
           # Build KD-tree for fast nearest neighbor search
           coords = [[s['lat'], s['lon']] for s in stations]
           self.tree = cKDTree(coords)
           self.aqi_values = [s['aqi'] for s in stations]
       
       def interpolate_aqi(self, lat, lon):
           # Find k nearest stations (k=5)
           dists, indices = self.tree.query([lat, lon], k=5)
           
           weights = 1.0 / (dists ** 2)
           weights[weights == np.inf] = 0  # Handle exact match
           
           total_weight = np.sum(weights)
           if total_weight == 0:
               return np.mean(self.aqi_values[indices])
           
           return np.sum(weights * self.aqi_values[indices]) / total_weight
   ```

2. **Vectorized Batch Processing:**
   ```python
   def batch_interpolate_aqi(self, points):
       """Interpolate AQI for multiple points at once"""
       points_array = np.array(points)
       dists, indices = self.tree.query(points_array, k=5)
       
       # Vectorized IDW
       weights = 1.0 / (dists ** 2)
       weights[weights == np.inf] = 0
       
       total_weights = np.sum(weights, axis=1)
       weighted_aqi = np.sum(weights * self.aqi_values[indices], axis=1)
       
       return weighted_aqi / total_weights
   ```

3. **Spatial Indexing Grid:** Pre-compute AQI on a grid
   ```python
   class GridAQIInterpolator:
       def __init__(self, stations, grid_resolution=0.01):
           self.stations = stations
           self.grid = self._build_grid(grid_resolution)
       
       def _build_grid(self, resolution):
           """Pre-compute AQI grid"""
           lats = np.arange(22.5, 22.7, resolution)
           lons = np.arange(88.3, 88.5, resolution)
           grid = {}
           
           for lat in lats:
               for lon in lons:
                   grid[(lat, lon)] = self._interpolate_at_point(lat, lon)
           
           return grid
       
       def interpolate_aqi(self, lat, lon):
           """Lookup nearest grid point"""
           grid_lat = round(lat / 0.01) * 0.01
           grid_lon = round(lon / 0.01) * 0.01
           return self.grid.get((grid_lat, grid_lon), 100.0)
   ```

---

## 5. Real-Time Station Integration Guide

### Step-by-Step Implementation

#### Step 1: Choose API Provider

| Provider | Coverage | Rate Limit | Auth Required | Recommendation |
|----------|----------|------------|---------------|----------------|
| WAQI | Global | 1000/day | Token (free) | ⭐ Best for Kolkata |
| OpenAQ | Global | Unlimited | None | ⭐ Good backup |
| CPCB | India | Unknown | API Key | Good for official data |

**Recommendation:** Use WAQI as primary, OpenAQ as backup.

#### Step 2: Get API Credentials

**WAQI:**
1. Go to https://aqicn.org/api/
2. Sign up for free account
3. Get token from email

**OpenAQ:**
- No signup required
- Free and unlimited

#### Step 3: Implement Fetcher

```bash
# Create new file
touch aqi_fetcher.py
```

Add the `AQIFetcher` code from Phase 2 above.

#### Step 4: Update Configuration

```bash
# Create config file
touch config.py
```

```python
# config.py
AQI_API_TYPE = 'waqi'  # or 'openaq', 'cpcb'
AQI_API_TOKEN = 'your_waqi_token_here'  # for WAQI
AQI_UPDATE_INTERVAL_MINUTES = 30
KOLKATA_BBOX = {
    'min_lat': 22.5,
    'max_lat': 22.7,
    'min_lon': 88.3,
    'max_lon': 88.5
}
```

#### Step 5: Replace Dummy Interpolator

```bash
# Backup old file
mv dummy_aqi_interpolator.py dummy_aqi_interpolator.py.backup

# Create new file
touch real_aqi_interpolator.py
```

Add the `RealAQIInterpolator` code from Phase 1 above.

#### Step 6: Update API Server

```python
# In dummy_api.py, replace:
from dummy_aqi_interpolator import DummyAQIInterpolator

# With:
from real_aqi_interpolator import RealAQIInterpolator
from aqi_fetcher import AQIFetcherFactory

# Initialize
fetcher = AQIFetcherFactory.create(
    config.AQI_API_TYPE,
    token=config.AQI_API_TOKEN
)
interpolator = RealAQIInterpolator(
    fetcher=fetcher,
    update_interval_minutes=config.AQI_UPDATE_INTERVAL_MINUTES
)
```

#### Step 7: Add Multi-Route Support

```python
# In enhanced_api.py (new file)
from enhanced_network import EnhancedGraphProcessor

processor = EnhancedGraphProcessor(G, interpolator)

# Add new endpoint
@app.route('/routes/clean/multi')
def get_multiple_clean_routes():
    """Get multiple clean routes with different sensitivities"""
    # ... implementation from Phase 4
```

#### Step 8: Test Integration

```bash
# Start server
python dummy_api.py

# Test endpoint
curl http://localhost:5002/stations

# Should return real station data
```

---

## 6. API Compatibility

### Current API (Keep Compatible)

| Endpoint | Current Response | Enhanced Response |
|----------|------------------|-------------------|
| `GET /` | "Dummy Data Version" | "Real-time Version" |
| `GET /stations` | Dummy stations | Real stations |
| `GET /routes/clean` | Single clean route | Multiple clean routes |
| `GET /test` | Sample route | Sample route |

### New Endpoints (Add)

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /routes/clean/multi` | Multiple clean routes | Array of routes |
| `GET /routes/clean/geojson` | GeoJSON format | GeoJSON FeatureCollection |
| `GET /config` | Get current config | Config object |
| `POST /config` | Update config | Confirmation |

---

## 7. Migration Checklist

- [ ] Choose AQI API provider (WAQI recommended)
- [ ] Get API credentials
- [ ] Implement `aqi_fetcher.py`
- [ ] Implement `real_aqi_interpolator.py`
- [ ] Implement `enhanced_network.py`
- [ ] Update `dummy_api.py` to use real interpolator
- [ ] Add multi-route support
- [ ] Add GeoJSON endpoint
- [ ] Test with real data
- [ ] Update documentation
- [ ] Deploy to production

---

## 8. Performance Targets

| Metric | Current (Dummy) | Target (Real-time) |
|--------|-----------------|-------------------|
| Station fetch time | 0ms (file) | < 2s (API) |
| Route calculation | 0.5-2s | < 3s (with cache) |
| API response time | < 3s | < 5s (with real data) |
| Update frequency | Manual | Every 30 min (auto) |
| Station count | 25 (fixed) | 20-50 (dynamic) |

---

## 9. Summary

### Key Takeaways

1. **Algorithm Compatibility:** Green Path's cost formula can be adapted to Kolkata's AQI scale with simple conversion.

2. **Data Layer Only Change:** Replace the data acquisition layer (dummy → real stations) while keeping the routing core (NetworkX + Dijkstra).

3. **Keep NetworkX:** No need to switch to igraph; NetworkX is sufficient for Kolkata's scale (~32K nodes).

4. **Add Multi-Route:** Implement Green Path's multi-sensitivity approach for better user choice.

5. **Performance Optimization:** Use KD-tree, batch processing, and pre-computation to handle real-time data efficiently.

6. **API Compatibility:** Maintain existing endpoints while adding new ones for advanced features.

### Recommended Implementation Order

1. **Week 1:** Implement real AQI fetcher (WAQI)
2. **Week 2:** Replace dummy interpolator with real interpolator
3. **Week 3:** Add edge cost pre-computation
4. **Week 4:** Implement multi-route support
5. **Week 5:** Add GeoJSON endpoint
6. **Week 6:** Testing and optimization

---

**Document Version:** 1.0  
**Last Updated:** May 11, 2026
