# Kolkata AQI Clean Route Project - Implementation Overview

## Project Concept
A pollution-aware routing system for Kolkata that helps users find cleaner routes by avoiding high Air Quality Index (AQI) areas using real-time data.

## System Architecture

### Backend (Python/Flask)
- **API Server**: Flask application on port 5002
- **Road Network**: 31,894 nodes, 79,000 edges from OpenStreetMap
- **AQI Data**: 97 real-time monitoring stations from WAQI API

### Frontend (HTML/CSS/JS)
- **Map Visualization**: Leaflet.js for interactive maps
- **User Interface**: Route planning with start/end points
- **Pollution Control**: Adjustable sensitivity slider

## API Integration

### WAQI (World Air Quality Index) API
- **Endpoint**: `https://api.waqi.info/v2/map/bounds/`
- **Parameters**: Bounding box coordinates (lat,lon bounds for Kolkata)
- **Data Retrieved**: Station name, AQI value, GPS coordinates
- **Coverage**: 20km radius around Kolkata center (22.5726, 88.3639)
- **Update Frequency**: Real-time with caching to minimize API calls

### Backend API Endpoints
- `GET /` - System status check
- `GET /stations` - Returns all AQI monitoring stations
- `GET /routes/clean` - Calculates clean vs fast routes
  - Parameters: start_lat, start_lon, end_lat, end_lon, pollution_factor

## Core Algorithm: Dijkstra with Pollution Weights

### 1. Fastest Route Calculation
```
Algorithm: Standard Dijkstra
Edge Weight: Travel time (based on road speed limits)
Goal: Minimize total travel time
```

**Process**:
1. Find nearest graph nodes to start/end coordinates
2. Apply Dijkstra's algorithm using `travel_time` as edge weight
3. Return shortest path by time

### 2. Cleanest Route Calculation
```
Algorithm: Modified Dijkstra with pollution penalty
Edge Weight: travel_time × (1 + pollution_factor × (AQI/100))
Goal: Minimize pollution exposure while considering time
```

**Process**:
1. Find nearest graph nodes to start/end coordinates
2. For each road segment (edge):
   - Calculate midpoint coordinates
   - Get AQI at midpoint using interpolation
   - Apply pollution penalty formula
3. Apply Dijkstra's algorithm using weighted edges
4. Return path avoiding high AQI areas

### Pollution Penalty Formula
```
weighted_time = travel_time × [1 + (pollution_factor × AQI/100)]

Where:
- travel_time: Base travel time for the road segment
- pollution_factor: User sensitivity (0-10, default 2.0)
- AQI: Air Quality Index at that location (0-500+)

Example:
- travel_time = 5 minutes
- AQI = 150 (unhealthy)
- pollution_factor = 2.0
- weighted_time = 5 × [1 + (2.0 × 150/100)] = 5 × 4 = 20 minutes
```

## AQI Interpolation (IDW)

### Inverse Distance Weighting
Since monitoring stations are discrete points, we estimate AQI at any location using:

```
AQI_point = Σ (AQI_station × weight) / Σ weight

Where:
- weight = 1 / (distance + 0.1)
- distance: Distance from point to station
```

**Purpose**: Estimate pollution levels between monitoring stations for accurate route analysis.


## Route Comparison

### Metrics Calculated
1. **Distance**: Total path length in kilometers
2. **Travel Time**: Estimated time based on road speeds
3. **Average AQI**: Mean pollution exposure along route
4. **Max/Min AQI**: Pollution hotspots and clean areas
5. **Pollution Exposure**: Distance × Average AQI

### Trade-off Analysis
```
Distance Increase % = ((Clean Distance - Fast Distance) / Fast Distance) × 100
AQI Improvement = Fast Average AQI - Clean Average AQI
```

### Example Comparison
```
Fast Route:
- Distance: 4.34 km
- Average AQI: 92.3
- Time: 12 minutes

Clean Route:
- Distance: 4.64 km (+6.9%)
- Average AQI: 89.2 (-3.1 AQI)
- Time: 13 minutes

Trade-off: 1 extra minute for 3.1 AQI improvement
```

## Data Flow

### User Request → Route Calculation
1. User selects start/end points on map
2. Frontend sends coordinates to backend API
3. Backend finds nearest road network nodes
4. Calculates both fastest and cleanest paths
5. Returns route coordinates and analysis
6. Frontend displays both routes on map with comparison

### Real-time Data Updates
1. WAQI API provides current AQI values
2. Data cached locally to reduce API calls
3. Stations refreshed periodically for accuracy
4. Route calculations use latest pollution data

## Key Technologies

- **Routing**: NetworkX (Dijkstra implementation)
- **Geospatial**: OSMnx (road network), GeoPy (distance calculations)
- **Interpolation**: SciPy (spatial distance calculations)
- **API**: Flask (backend), WAQI (AQI data)
- **Frontend**: Leaflet.js (maps), vanilla JavaScript

## AQI Station Selection During Route Travel

### How Stations Are Selected
The system does NOT select specific stations for each route. Instead, it uses **all available stations** in the Kolkata area and applies interpolation:

1. **All Stations Loaded**: 97 AQI monitoring stations are loaded at startup from WAQI API
2. **Spatial Coverage**: Stations cover 20km radius around Kolkata center
3. **Dynamic Estimation**: For any point on the route, the system estimates AQI using nearby stations

### Interpolation Process (IDW)
When calculating pollution at a specific road segment:

```
Step 1: Identify all stations with valid AQI data
Step 2: Calculate distance from road point to each station
Step 3: Apply weights based on distance (closer = higher weight)
Step 4: Calculate weighted average of nearby stations

Formula:
weight_i = 1 / (distance_i + 0.1)
AQI_point = Σ (AQI_i × weight_i) / Σ weight_i
```

**Example**: If a road point is 0.5km from Station A (AQI=80) and 2km from Station B (AQI=120):
- Weight A = 1/(0.5+0.1) = 1.67
- Weight B = 1/(2+0.1) = 0.48
- AQI_point = (80×1.67 + 120×0.48) / (1.67+0.48) = 91.2

### Why This Approach?
- **No Pre-selection**: Uses all available data for accuracy
- **Smooth Transitions**: Interpolation provides continuous AQI estimates
- **Adaptive**: Works even if route passes far from any station
- **Real-time**: Uses latest AQI values from all stations

## Detailed Route Comparison Process

### Step-by-Step Comparison

**Step 1: Calculate Both Routes**
- Fastest route: Standard Dijkstra (minimize travel time)
- Cleanest route: Pollution-weighted Dijkstra (minimize pollution exposure)

**Step 2: Analyze Each Route**
For every road segment in both routes:
- Get midpoint coordinates
- Estimate AQI at midpoint using IDW interpolation
- Calculate segment distance and travel time
- Accumulate statistics

**Step 3: Compute Metrics**

**For Fast Route:**
```
total_distance = Σ segment_distances
total_time = Σ segment_travel_times
aqi_values = [AQI at each segment midpoint]
average_aqi = mean(aqi_values)
max_aqi = max(aqi_values)
min_aqi = min(aqi_values)
pollution_exposure = total_distance × average_aqi
```

**For Clean Route:**
```
(Same calculations as fast route)
```

**Step 4: Compare Results**
```
distance_increase = ((clean_distance - fast_distance) / fast_distance) × 100
time_increase = ((clean_time - fast_time) / fast_time) × 100
aqi_improvement = fast_average_aqi - clean_average_aqi
exposure_reduction = fast_pollution_exposure - clean_pollution_exposure
```

### Decision Logic
The system presents both routes to the user with trade-offs:
- **Fast Route**: Shorter time, higher pollution exposure
- **Clean Route**: Lower pollution, potentially longer distance/time
- **User Choice**: User can select based on their priority (speed vs health)

## Navigation Through Points

### Road Network Representation
The Kolkata road network is represented as a graph:
- **Nodes**: 31,894 intersections/junctions (each with GPS coordinates)
- **Edges**: 79,000 road segments connecting nodes
- **Edge Attributes**: travel_time, distance, road type

### Point-to-Point Navigation

**Step 1: Find Nearest Nodes**
```
Input: User's start/end GPS coordinates
Process:
- For each graph node, calculate distance to user's point
- Select node with minimum distance (using geodesic distance)
- This becomes the start/end node for routing

Example:
User point: (22.5726, 88.3639)
Nearest node: Node #15472 at (22.5728, 88.3641)
Distance: 25 meters
```

**Step 2: Apply Dijkstra's Algorithm**
```
For Fastest Route:
- Use travel_time as edge weight
- Find shortest path from start_node to end_node
- Returns: [node_15472, node_15473, node_15480, ..., node_28901]

For Cleanest Route:
- Use pollution_weighted_time as edge weight
- Find shortest path from start_node to end_node
- Returns: [node_15472, node_15475, node_15490, ..., node_28901]
```

**Step 3: Convert Nodes to Coordinates**
```
For each node in the path:
- Get node's GPS coordinates (lat, lon) from graph
- Create coordinate array: [[lat1, lon1], [lat2, lon2], ...]
- Return to frontend for map display
```

**Step 4: Real-time Navigation**
The system provides:
- **Route coordinates**: Array of GPS points
- **Turn-by-turn**: Not implemented (current version shows full route)
- **Pollution heatmap**: AQI values along the route
- **Alternative routes**: Fast vs Clean options

### Navigation Accuracy
- **Node resolution**: ~25-50 meters between nodes
- **Road coverage**: All major and minor roads in Kolkata
- **Real-time updates**: AQI data refreshed periodically
- **Dynamic routing**: Can recalculate if pollution conditions change

## Implementation Summary

The system uses a modified Dijkstra algorithm where road segments in high-pollution areas are artificially "longer" (higher weight), causing the routing algorithm to prefer cleaner paths. The pollution factor allows users to control how much they want to avoid pollution - higher values prioritize clean air over speed, while lower values prioritize speed over air quality.

Real-time AQI data from WAQI ensures routes reflect current pollution conditions, and interpolation provides smooth pollution estimates between monitoring stations for accurate route analysis.
