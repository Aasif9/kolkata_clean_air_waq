# Kolkata Clean Air Routes - Complete System Overview

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Graph Storage & Node/Edge Calculation](#graph-storage--nodeedge-calculation)
3. [API Endpoints & Data Flow](#api-endpoints--data-flow)
4. [Algorithm Implementations](#algorithm-implementations)
5. [Route Calculation Process](#route-calculation-process)
6. [AQI Analysis & Exposure Calculation](#aqi-analysis--exposure-calculation)

---

## System Architecture

### High-Level Architecture
```
┌─────────────────┐
│   Frontend      │
│   (React/HTML)  │
└────────┬────────┘
         │ HTTP Requests
         ↓
┌─────────────────┐
│   Flask API     │
│  (dummy_api.py) │
└────────┬────────┘
         │
    ┌────┴────┬────────────┐
    ↓         ↓            ↓
┌────────┐ ┌────────┐ ┌────────────┐
│ Graph  │ │ AQI    │ │  Router    │
│ Network│ │Service │ │ Algorithm  │
└────────┘ └────────┘ └────────────┘
    ↓         ↓            ↓
┌────────┐ ┌────────┐ ┌────────────┐
│ .pkl   │ │ WAQI   │ │ Dijkstra   │
│ File   │ │ API    │ │ Algorithm  │
└────────┘ └────────┘ └────────────┘
```

### Component Overview
1. **Frontend**: Web interface for route planning (HTML/JavaScript)
2. **Flask API**: REST API server handling HTTP requests
3. **Graph Network**: Road network data structure
4. **AQI Service**: Air quality data management and interpolation
5. **Router**: Pollution-aware routing algorithm

---

## Graph Storage & Node/Edge Calculation

### 1. Graph Creation Process

#### File: `basic_network.py`

**Step 1: Define Geographic Bounds**
```python
# Kolkata center coordinates
center_lat = 22.5726
center_lon = 88.3639

# 15km square region (7.5km in each direction from center)
lat_range = 0.0675  # ~7.5km in latitude
lon_range = 0.0675  # ~7.5km in longitude

# Calculate bounds
north = center_lat + lat_range  # 22.6401
south = center_lat - lat_range  # 22.5051
east = center_lon + lon_range   # 88.4314
west = center_lon - lon_range   # 88.2964
```

**Step 2: Download Road Network from OpenStreetMap**
```python
import osmnx as ox

# Download network using OSMnx
graph = ox.graph_from_bbox(
    north, south, east, west,
    network_type='drive',  # Only drivable roads
    simplify=True,         # Simplify topology
    retain_all=True        # Keep all attributes
)
```

**Step 3: Add Edge Weights (Travel Time)**
```python
# Add speed limits to edges
graph = ox.add_edge_speeds(graph)

# Calculate travel time based on speed and distance
graph = ox.add_edge_travel_times(graph)
```

**Step 4: Graph Structure**
- **Nodes**: Intersections and road endpoints
  - Each node contains:
    - `y`: Latitude coordinate
    - `x`: Longitude coordinate
    - `osmid`: OpenStreetMap ID
    - Other OSM attributes

- **Edges**: Road segments connecting nodes
  - Each edge contains:
    - `length`: Physical length in meters
    - `speed_kph`: Speed limit in km/h
    - `travel_time`: Time to traverse in minutes
    - `geometry`: Road geometry (curved roads)
    - Other OSM attributes

**Step 5: Save Graph to File**
```python
import pickle

# Save as binary pickle file
with open('kolkata_road_network.pkl', 'wb') as f:
    pickle.dump(graph, f)
```

**Storage Location**: `kolkata_road_network.pkl` (16MB file)
- **Format**: Binary pickle serialization
- **Contents**: Complete NetworkX graph object
- **Size**: ~31,894 nodes, ~50,000+ edges
- **Persistence**: Permanent storage on disk

### 2. Graph Loading Process

**File: `dummy_api.py` (lines 23-30)**
```python
def initialize_system():
    global graph, interpolator, router
    
    # Load network from pickle file
    with open('kolkata_road_network.pkl', 'rb') as f:
        graph = pickle.load(f)
    
    print(f"Loaded network: {len(graph.nodes)} nodes")
```

**Loading Steps**:
1. Open pickle file in binary read mode
2. Deserialize NetworkX graph object
3. Store in global variable for API access
4. Graph is now ready for routing operations

### 3. Node/Edge Data Structure

**Node Example**:
```python
{
    'y': 22.5726,           # Latitude
    'x': 88.3639,           # Longitude
    'osmid': 12345678,      # OpenStreetMap ID
    'street_count': 3,      # Number of streets meeting
    'highway': 'traffic_signals'  # Node type
}
```

**Edge Example**:
```python
{
    'length': 125.5,        # Length in meters
    'speed_kph': 40.0,      # Speed limit km/h
    'travel_time': 0.188,   # Travel time in minutes
    'geometry': LineString([...]),  # Road shape
    'highway': 'primary',   # Road type
    'name': 'AJC Bose Road' # Street name
}
```

---

## API Endpoints & Data Flow

### 1. API Server Initialization

**File: `dummy_api.py`**

**Initialization Sequence**:
```python
def initialize_system():
    # Step 1: Load road network
    graph = pickle.load('kolkata_road_network.pkl')
    
    # Step 2: Initialize AQI service
    interpolator = AQIInterpolator()  # Loads WAQI stations
    
    # Step 3: Create router
    router = SimplePollutionRouter(graph, interpolator)
    
    return True
```

**Startup Process**:
1. Load road network from pickle file
2. Fetch AQI stations from WAQI API (or load from cache)
3. Initialize interpolation service
4. Create router with graph and AQI data
5. Start Flask server on port 5002

### 2. API Endpoints

#### Endpoint 1: `GET /`
**Purpose**: System status check
**Response**: String indicating data source
```python
@app.route('/')
def home():
    return "Kolkata AQI Routing - REAL Data Version"
```

#### Endpoint 2: `GET /stations`
**Purpose**: Get all AQI monitoring stations
**Response**: JSON with station data
```python
@app.route('/stations')
def get_stations():
    station_info = interpolator.get_station_info()
    return jsonify({
        'stations': station_info['stations'],
        'total_stations': station_info['total_stations'],
        'aqi_range': station_info['aqi_range'],
        'average_aqi': station_info['average_aqi'],
        'data_source': 'real'
    })
```

**Data Flow**:
1. API receives request
2. Calls `interpolator.get_station_info()`
3. AQI service returns cached station data
4. Returns JSON with 97 stations and statistics

#### Endpoint 3: `GET /routes/clean`
**Purpose**: Calculate clean vs fast routes
**Parameters**:
- `start_lat`, `start_lon`: Start coordinates
- `end_lat`, `end_lon`: End coordinates
- `pollution_factor`: Pollution sensitivity (default 2.0)

**Response**: JSON with both routes and analysis
```python
@app.route('/routes/clean')
def get_clean_route():
    # Extract parameters
    start_lat = float(request.args.get('start_lat'))
    start_lon = float(request.args.get('start_lon'))
    end_lat = float(request.args.get('end_lat'))
    end_lon = float(request.args.get('end_lon'))
    pollution_factor = float(request.args.get('pollution_factor', 2.0))
    
    # Update pollution factor
    router.pollution_factor = pollution_factor
    
    # Find both routes
    clean_path = router.find_cleanest_path(start_lat, start_lon, end_lat, end_lon)
    fast_path = router.find_fastest_path(start_lat, start_lon, end_lat, end_lon)
    
    # Analyze routes
    clean_analysis = router.analyze_path_pollution(clean_path)
    fast_analysis = router.analyze_path_pollution(fast_path)
    
    # Convert to coordinates with AQI
    clean_waypoints = path_to_coords_with_aqi(clean_path)
    fast_coordinates = path_to_coordinates(fast_path)
    
    # Calculate comparison
    comparison = calculate_comparison(clean_analysis, fast_analysis)
    
    return jsonify({
        'clean_route': {'waypoints': clean_waypoints, 'analysis': clean_analysis},
        'fast_route': {'coordinates': fast_coordinates, 'analysis': fast_analysis},
        'comparison': comparison
    })
```

### 3. Complete Data Flow for Route Calculation

```
User Request (Frontend)
    ↓
HTTP GET /routes/clean?start_lat=X&start_lon=Y&end_lat=A&end_lon=B
    ↓
Flask API (dummy_api.py)
    ↓
Extract coordinates and pollution factor
    ↓
SimplePollutionRouter.find_fastest_path()
    ↓
Find nearest graph nodes to start/end points
    ↓
NetworkX Dijkstra algorithm (weight: travel_time)
    ↓
Return fastest path (list of node IDs)
    ↓
SimplePollutionRouter.find_cleanest_path()
    ↓
Find nearest graph nodes to start/end points
    ↓
Custom weight function with pollution penalty
    ↓
NetworkX Dijkstra algorithm (weight: pollution_weight)
    ↓
Return cleanest path (list of node IDs)
    ↓
SimplePollutionRouter.analyze_path_pollution()
    ↓
For each edge in path:
    - Calculate distance (geodesic)
    - Get AQI at midpoint (interpolation)
    - Accumulate distance, time, AQI values
    ↓
Calculate statistics (avg AQI, max/min, exposure)
    ↓
Convert paths to coordinates with AQI values
    ↓
Calculate comparison metrics
    ↓
Return JSON response to frontend
```

---

## Algorithm Implementations

### 1. Nearest Node Finding Algorithm

**File: `simple_router.py` (lines 73-91)**

**Purpose**: Find the graph node closest to given coordinates

**Algorithm Steps**:
```python
def _find_graph_node(self, lat, lon):
    min_dist = float('inf')
    nearest_node = None
    
    # Iterate through all graph nodes
    for node in self.graph.nodes():
        node_data = self.graph.nodes[node]
        node_lat = node_data['y']
        node_lon = node_data['x']
        
        # Calculate geodesic distance
        distance = geodesic((lat, lon), (node_lat, node_lon)).meters
        
        # Keep track of minimum distance
        if distance < min_dist:
            min_dist = distance
            nearest_node = node
    
    return nearest_node
```

**Time Complexity**: O(n) where n = number of nodes (31,894)
**Space Complexity**: O(1)
**Optimization Note**: Could use spatial indexing (KD-tree) for O(log n) lookup

### 2. Fastest Path Algorithm (Dijkstra)

**File: `simple_router.py` (lines 11-30)**

**Purpose**: Find shortest path by travel time

**Algorithm Steps**:
```python
def find_fastest_path(self, start_lat, start_lon, end_lat, end_lon):
    # Step 1: Find nearest graph nodes
    start_node = self._find_graph_node(start_lat, start_lon)
    end_node = self._find_graph_node(end_lat, end_lon)
    
    # Step 2: Apply Dijkstra's algorithm
    path = nx.shortest_path(
        self.graph,
        source=start_node,
        target=end_node,
        weight='travel_time'  # Edge weight = travel time in minutes
    )
    
    return path
```

**Dijkstra's Algorithm**:
1. Initialize distances: start_node = 0, all others = ∞
2. Use priority queue to select unvisited node with minimum distance
3. For each neighbor, calculate new distance = current + edge weight
4. If new distance < stored distance, update
5. Mark node as visited when extracted from queue
6. Repeat until target node is reached

**Time Complexity**: O((V + E) log V) where V = nodes, E = edges
**Space Complexity**: O(V)

**Edge Weight**: `travel_time` (pre-calculated in minutes)
- Formula: `travel_time = (length_meters / 1000) / speed_kph * 60`

### 3. Cleanest Path Algorithm (Pollution-Aware Dijkstra)

**File: `simple_router.py` (lines 32-71)**

**Purpose**: Find path minimizing pollution exposure

**Algorithm Steps**:
```python
def find_cleanest_path(self, start_lat, start_lon, end_lat, end_lon):
    # Step 1: Find nearest graph nodes
    start_node = self._find_graph_node(start_lat, start_lon)
    end_node = self._find_graph_node(end_lat, end_lon)
    
    # Step 2: Define custom weight function
    def pollution_weight(u, v, d):
        # Base travel time
        travel_time = d.get('travel_time', 1)
        
        # Get edge midpoint coordinates
        u_data = self.graph.nodes[u]
        v_data = self.graph.nodes[v]
        mid_lat = (u_data['y'] + v_data['y']) / 2
        mid_lon = (u_data['x'] + v_data['x']) / 2
        
        # Get AQI at midpoint via interpolation
        aqi = self.aqi_interpolator.get_aqi_at_point(mid_lat, mid_lon)
        
        # Calculate pollution penalty
        pollution_penalty = 1 + (self.pollution_factor * (aqi / 100))
        
        # Return weighted travel time
        return travel_time * pollution_penalty
    
    # Step 3: Apply Dijkstra with custom weight
    path = nx.shortest_path(
        self.graph,
        source=start_node,
        target=end_node,
        weight=pollution_weight
    )
    
    return path
```

**Pollution Weight Formula**:
```
weighted_time = travel_time × (1 + pollution_factor × (AQI / 100))
```

**Example Calculation**:
- travel_time = 2 minutes
- AQI = 75
- pollution_factor = 2.0
- weighted_time = 2 × (1 + 2.0 × (75/100)) = 2 × 2.5 = 5 minutes

**Effect**: Higher AQI edges have higher effective cost, causing algorithm to avoid them

**Time Complexity**: O((V + E) log V) × O(interpolation)
**Space Complexity**: O(V)

### 4. AQI Interpolation Algorithm (IDW)

**File: `aqi_service.py` (lines 86-111)**

**Purpose**: Estimate AQI at any point using nearby stations

**Algorithm: Inverse Distance Weighting (IDW)**

**Steps**:
```python
def _inverse_distance_weighting(self, lat, lon, power=2):
    # Step 1: Create coordinate arrays
    point = np.array([lat, lon])
    station_coords = np.array([[s['lat'], s['lon']] for s in self.stations])
    
    # Step 2: Calculate distances to all stations
    distances = cdist([point], station_coords)[0]
    
    # Step 3: Check for very close station (< 0.001 degrees)
    min_dist_idx = np.argmin(distances)
    if distances[min_dist_idx] < 0.001:
        return self.stations[min_dist_idx]['aqi']
    
    # Step 4: Filter valid stations (have AQI data)
    valid_indices = [i for i, s in enumerate(self.stations) if s['aqi'] is not None]
    
    # Step 5: Calculate weights using inverse distance
    valid_distances = distances[valid_indices]
    valid_weights = 1 / (valid_distances + 0.1)  # +0.1 to avoid division by zero
    valid_weights = valid_weights / valid_weights.sum()  # Normalize
    
    # Step 6: Calculate weighted average
    valid_aqi = np.array([self.stations[i]['aqi'] for i in valid_indices])
    interpolated_aqi = np.sum(valid_weights * valid_aqi)
    
    return interpolated_aqi
```

**IDW Formula**:
```
AQI_point = Σ (AQI_station × weight) / Σ weight
weight = 1 / (distance^power)
```

**Example**:
- Point at (22.57, 88.36)
- Station 1: AQI=70, distance=2km, weight=1/4=0.25
- Station 2: AQI=80, distance=1km, weight=1/1=1.0
- Station 3: AQI=60, distance=3km, weight=1/9=0.11
- Normalized weights: [0.18, 0.73, 0.09]
- Interpolated AQI = 70×0.18 + 80×0.73 + 60×0.09 = 75.4

**Time Complexity**: O(n) where n = number of stations (97)
**Space Complexity**: O(n)

### 5. WAQI API Data Fetching

**File: `real_aqi_fetcher.py` (lines 43-73)**

**Purpose**: Fetch real-time AQI stations from WAQI API

**Steps**:
```python
def _fetch_waqi_bounds(self, bounds=None):
    # Step 1: Get API token
    token = self._get_token()  # From file or environment
    
    # Step 2: Set geographic bounds
    if not bounds:
        bounds = "22.390,88.150,22.750,88.550"  # Kolkata region
    
    # Step 3: Construct API URL
    url = f"https://api.waqi.info/v2/map/bounds/?latlng={bounds}&token={token}"
    
    # Step 4: Make HTTP request
    response = requests.get(url, timeout=30)
    data = response.json()
    
    # Step 5: Extract station data
    if data['status'] == 'ok':
        stations = data['data']
        return self._normalize_waqi_stations(stations)
```

**API Response Structure**:
```json
{
  "status": "ok",
  "data": [
    {
      "idx": 1234,
      "aqi": 75,
      "lat": 22.5726,
      "lon": 88.3639,
      "station": {"name": "Victoria Memorial"}
    }
  ]
}
```

**Normalization**:
```python
def _normalize_waqi_stations(self, stations):
    normalized = []
    for station in stations:
        normalized.append({
            'name': station['station']['name'],
            'aqi': float(station['aqi']),
            'lat': float(station['lat']),
            'lon': float(station['lon']),
            'station_id': f"waqi_{station['idx']}"
        })
    return normalized
```

**Caching**: Stations saved to `kolkata_real_stations.json` to avoid repeated API calls

---

## Route Calculation Process

### 1. Complete Route Calculation Flow

```
User selects start and end points on map
    ↓
Frontend sends: GET /routes/clean?start_lat=X&start_lon=Y&end_lat=A&end_lon=B
    ↓
Backend: dummy_api.py
    ↓
Extract parameters:
  - start_lat, start_lon, end_lat, end_lon
  - pollution_factor (default 2.0)
    ↓
Router: SimplePollutionRouter
    ↓
┌─────────────────────────────────────┐
│  FAST ROUTE CALCULATION             │
├─────────────────────────────────────┤
│  1. Find nearest nodes              │
│     - start_node = nearest(start)   │
│     - end_node = nearest(end)       │
│                                     │
│  2. Dijkstra algorithm             │
│     - weight = travel_time         │
│     - Returns: node sequence        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  CLEAN ROUTE CALCULATION           │
├─────────────────────────────────────┤
│  1. Find nearest nodes              │
│     - start_node = nearest(start)   │
│     - end_node = nearest(end)       │
│                                     │
│  2. Custom weight function          │
│     - For each edge:               │
│       a. Get midpoint coords       │
│       b. Interpolate AQI           │
│       c. Calculate penalty         │
│       d. weight = time × penalty   │
│                                     │
│  3. Dijkstra algorithm             │
│     - weight = pollution_weight    │
│     - Returns: node sequence        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  PATH ANALYSIS                     │
├─────────────────────────────────────┤
│  For each path (fast & clean):     │
│  1. Initialize counters            │
│     - total_distance = 0           │
│     - total_time = 0               │
│     - aqi_values = []              │
│                                     │
│  2. For each edge in path:         │
│     a. Calculate distance          │
│        (geodesic formula)           │
│     b. Get travel time from graph   │
│     c. Get midpoint coordinates    │
│     d. Interpolate AQI at midpoint  │
│     e. Accumulate values            │
│                                     │
│  3. Calculate statistics           │
│     - average_aqi = mean(aqi)      │
│     - max_aqi = max(aqi)           │
│     - min_aqi = min(aqi)           │
│     - exposure = distance × avg    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  COORDINATE CONVERSION             │
├─────────────────────────────────────┤
│  Clean route:                      │
│  - For each node:                  │
│    a. Get lat, lon from graph      │
│    b. Interpolate AQI at node      │
│    c. Create waypoint object       │
│                                     │
│  Fast route:                       │
│  - For each node:                  │
│    a. Get lat, lon from graph      │
│    b. Create coordinate array      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  COMPARISON CALCULATION            │
├─────────────────────────────────────┤
│  distance_increase =               │
│    (clean_dist - fast_dist) /      │
│    fast_dist × 100                 │
│                                     │
│  aqi_improvement =                 │
│    fast_aqi - clean_aqi            │
└─────────────────────────────────────┘
    ↓
Return JSON response to frontend
```

### 2. Detailed Step-by-Step Example

**Input**:
- Start: (22.5750, 88.3500) - Howrah
- End: (22.5800, 88.3800) - Salt Lake
- Pollution factor: 2.0

**Step 1: Find Nearest Nodes**
```
Start: (22.5750, 88.3500)
  → Search all 31,894 nodes
  → Find node #4521 at (22.5751, 88.3502), distance=25m

End: (22.5800, 88.3800)
  → Search all 31,894 nodes
  → Find node #8934 at (22.5801, 88.3801), distance=18m
```

**Step 2: Fastest Path (Dijkstra)**
```
Graph: 31,894 nodes, 50,000+ edges
Algorithm: Dijkstra with weight='travel_time'

Process:
  - Priority queue: [(0, 4521), (∞, ...), ...]
  - Extract 4521 (distance=0)
  - Update neighbors: [(2.5, 7823), (1.8, 3341), ...]
  - Extract 3341 (distance=1.8)
  - Update neighbors: [(3.2, 4451), (2.1, 7823), ...]
  - Continue until 8931 is reached

Result: [4521, 3341, 4451, 7823, ..., 8934]
       (37 nodes)
```

**Step 3: Cleanest Path (Pollution-Aware Dijkstra)**
```
Graph: Same as above
Algorithm: Dijkstra with custom weight function

Custom weight calculation for each edge:
  Edge 4521→3341:
    - Midpoint: (22.57505, 88.3501)
    - Interpolated AQI: 72.5
    - Base travel_time: 1.8 min
    - Pollution penalty: 1 + 2.0 × (72.5/100) = 2.45
    - Weighted time: 1.8 × 2.45 = 4.41 min
  
  Edge 3341→4451:
    - Midpoint: (22.5753, 88.3505)
    - Interpolated AQI: 68.2
    - Base travel_time: 1.4 min
    - Pollution penalty: 1 + 2.0 × (68.2/100) = 2.36
    - Weighted time: 1.4 × 2.36 = 3.30 min

Process:
  - Priority queue uses weighted times
  - Algorithm avoids high-AQI edges
  - May take longer path through cleaner areas

Result: [4521, 5567, 2234, 8891, ..., 8934]
       (55 nodes - longer but cleaner)
```

**Step 4: Path Analysis**
```
Fast path analysis (37 edges):
  Edge 1: distance=0.12km, time=1.8min, AQI=72.5
  Edge 2: distance=0.08km, time=1.4min, AQI=68.2
  Edge 3: distance=0.15km, time=2.1min, AQI=75.1
  ...
  Edge 37: distance=0.10km, time=1.5min, AQI=71.3
  
  Total distance: 3.37 km
  Total time: 275.4 min
  AQI values: [72.5, 68.2, 75.1, ..., 71.3]
  
  Average AQI: 71.63
  Max AQI: 75.0
  Min AQI: 71.24
  Exposure: 3.37 × 71.63 = 241.1

Clean path analysis (55 edges):
  Edge 1: distance=0.10km, time=1.5min, AQI=68.5
  Edge 2: distance=0.12km, time=1.8min, AQI=65.2
  Edge 3: distance=0.14km, time=2.0min, AQI=69.8
  ...
  Edge 55: distance=0.11km, time=1.6min, AQI=71.2
  
  Total distance: 16.94 km
  Total time: 1466.8 min
  AQI values: [68.5, 65.2, 69.8, ..., 71.2]
  
  Average AQI: 71.42
  Max AQI: 72.06
  Min AQI: 61.0
  Exposure: 16.94 × 71.42 = 1209.8
```

**Step 5: Comparison**
```
Distance increase: (16.94 - 3.37) / 3.37 × 100 = 403%
AQI improvement: 71.63 - 71.42 = 0.21
```

---

## AQI Analysis & Exposure Calculation

### 1. Path Pollution Analysis Algorithm

**File: `simple_router.py` (lines 93-155)**

**Purpose**: Calculate pollution metrics for a given path

**Step-by-Step Process**:

```python
def analyze_path_pollution(self, path):
    # Step 1: Initialize accumulators
    total_distance = 0.0
    total_travel_time = 0.0
    aqi_values = []
    
    # Step 2: Process each edge in path
    for i in range(len(path) - 1):
        u = path[i]      # Current node
        v = path[i + 1]  # Next node
        
        # Step 2a: Get node coordinates
        u_data = self.graph.nodes[u]
        v_data = self.graph.nodes[v]
        
        # Step 2b: Calculate geodesic distance
        distance = geodesic(
            (u_data['y'], u_data['x']),
            (v_data['y'], v_data['x'])
        ).kilometers
        
        # Step 2c: Get edge travel time
        edge_data = self.graph.get_edge_data(u, v)
        edge = list(edge_data.values())[0]
        travel_time = edge.get('travel_time', distance * 2)
        
        # Step 2d: Calculate midpoint coordinates
        mid_lat = (u_data['y'] + v_data['y']) / 2
        mid_lon = (u_data['x'] + v_data['x']) / 2
        
        # Step 2e: Interpolate AQI at midpoint
        aqi = self.aqi_interpolator.get_aqi_at_point(mid_lat, mid_lon)
        
        # Step 2f: Accumulate values
        total_distance += distance
        total_travel_time += travel_time
        aqi_values.append(aqi)
    
    # Step 3: Calculate statistics
    average_aqi = np.mean(aqi_values)
    max_aqi = np.max(aqi_values)
    min_aqi = np.min(aqi_values)
    pollution_exposure = total_distance * average_aqi
    
    # Step 4: Return analysis
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

### 2. Average AQI Calculation

**Formula**:
```
average_aqi = (Σ aqi_values) / n
```

**Example**:
```
AQI values: [72.5, 68.2, 75.1, 71.3, 69.8]
Sum: 356.9
Count: 5
Average: 356.9 / 5 = 71.38
```

**Implementation**: Uses NumPy's `mean()` function for efficiency
```python
average_aqi = np.mean(aqi_values)
```

### 3. Pollution Exposure Calculation

**Formula**:
```
pollution_exposure = total_distance_km × average_aqi
```

**Purpose**: Measures total pollution exposure along the route
- Higher distance = more exposure
- Higher AQI = more exposure
- Units: AQI-kilometers (composite metric)

**Example**:
```
Total distance: 16.94 km
Average AQI: 71.42
Exposure: 16.94 × 71.42 = 1209.8 AQI-km
```

**Interpretation**:
- Higher exposure = worse air quality experience
- Used to compare routes: lower exposure is better
- Accounts for both distance and pollution level

### 4. AQI Interpolation at Midpoints

**Why Midpoints?**
- AQI varies continuously across space
- Edge endpoints may not represent average pollution
- Midpoint gives better estimate of edge's pollution level

**Process**:
```python
# For edge from node A to node B:
mid_lat = (lat_A + lat_B) / 2
mid_lon = (lon_A + lon_B) / 2
aqi = interpolator.get_aqi_at_point(mid_lat, mid_lon)
```

**IDW Interpolation** (detailed):
```python
# Get all station coordinates
station_coords = [[s['lat'], s['lon']] for s in stations]

# Calculate distances from midpoint to all stations
distances = [geodesic(mid, station).km for station in station_coords]

# Calculate weights (inverse distance)
weights = [1 / (d + 0.1) for d in distances]

# Normalize weights
total_weight = sum(weights)
normalized_weights = [w / total_weight for w in weights]

# Calculate weighted average
interpolated_aqi = sum(w * aqi for w, aqi in zip(normalized_weights, station_aqis))
```

### 5. Complete AQI Analysis Example

**Route**: 55 edges from Howrah to Salt Lake

**Edge-by-Edge Processing**:
```
Edge 1: Howrah Road
  - Start: (22.5750, 88.3500)
  - End: (22.5755, 88.3505)
  - Distance: 0.07 km
  - Midpoint: (22.57525, 88.35025)
  - Nearby stations:
    * Station A: AQI=70, distance=1.2km, weight=0.83
    * Station B: AQI=75, distance=2.5km, weight=0.40
    * Station C: AQI=68, distance=0.8km, weight=1.25
  - Normalized weights: [0.34, 0.16, 0.50]
  - Interpolated AQI: 70×0.34 + 75×0.16 + 68×0.50 = 70.2
  - Travel time: 1.5 min

Edge 2: AJC Bose Road
  - Start: (22.5755, 88.3505)
  - End: (22.5760, 88.3510)
  - Distance: 0.08 km
  - Midpoint: (22.57575, 88.35075)
  - Interpolated AQI: 72.8
  - Travel time: 1.8 min

... (continue for all 55 edges)

Accumulation:
  Total distance: 16.94 km
  Total time: 1466.8 min
  AQI samples: [70.2, 72.8, 69.5, ..., 71.2] (55 values)

Statistics:
  Average AQI: 71.42
  Max AQI: 72.06
  Min AQI: 61.0
  Exposure: 16.94 × 71.42 = 1209.8 AQI-km
```

### 6. Route Comparison Metrics

**Distance Increase Percentage**:
```python
distance_increase = (
    (clean_distance - fast_distance) / fast_distance
) × 100
```

**Example**:
```
Clean distance: 16.94 km
Fast distance: 3.37 km
Increase: (16.94 - 3.37) / 3.37 × 100 = 403%
```

**AQI Improvement**:
```python
aqi_improvement = fast_average_aqi - clean_average_aqi
```

**Example**:
```
Fast AQI: 71.63
Clean AQI: 71.42
Improvement: 71.63 - 71.42 = 0.21
```

**Interpretation**:
- Positive improvement = clean route has better air quality
- Negative improvement = clean route has worse air quality
- Small values indicate similar air quality

---

## Summary

### System Components
1. **Graph Storage**: `kolkata_road_network.pkl` (31,894 nodes, 50,000+ edges)
2. **AQI Data**: 97 real-time stations from WAQI API
3. **API Server**: Flask on port 5002
4. **Frontend**: HTML/JavaScript on port 8001

### Key Algorithms
1. **Dijkstra**: Fastest path (O((V+E) log V))
2. **Pollution-Aware Dijkstra**: Cleanest path with AQI weights
3. **IDW Interpolation**: AQI estimation at any point
4. **Geodesic Distance**: Accurate distance calculation
5. **Nearest Neighbor**: Graph node finding

### Data Flow
```
User → Frontend → API → Router → Graph + AQI → Analysis → Response
```

### Performance
- Graph loading: ~2 seconds (from pickle)
- AQI loading: ~1 second (from cache)
- Route calculation: ~1-3 seconds
- Total response time: ~5-10 seconds

### Storage
- Road network: 16MB (pickle file)
- AQI stations: ~50KB (JSON cache)
- LocalStorage: ~5-10MB (user routes)
