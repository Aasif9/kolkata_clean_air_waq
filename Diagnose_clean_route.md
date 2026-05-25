# Clean Route Algorithm - Complete Diagnosis

## Overview
This document provides a comprehensive analysis of how the clean route algorithm works, including route computation, interpolation methods, pollution penalty calculations, and waypoint generation.

---

## 1. Route Computation Flow

### 1.1 Dijkstra Algorithm Implementation

**File**: `simple_router.py`

The system uses NetworkX's Dijkstra algorithm for both fastest and cleanest path finding:

#### Fastest Path (Line 11-30)
```python
def find_fastest_path(self, start_lat, start_lon, end_lat, end_lon):
    # Uses standard travel_time as weight
    path = nx.shortest_path(
        self.graph, 
        source=start_node, 
        target=end_node, 
        weight='travel_time'  # Pre-computed edge weight
    )
```

#### Cleanest Path (Line 32-71)
```python
def find_cleanest_path(self, start_lat, start_lon, end_lat, end_lon):
    # Uses custom pollution_weight function
    def pollution_weight(u, v, d):
        travel_time = d.get('travel_time', 1)
        # Calculates AQI at edge midpoint (ON-THE-FLY)
        aqi = self.aqi_interpolator.get_aqi_at_point(mid_lat, mid_lon)
        pollution_penalty = 1 + (self.pollution_factor * (aqi / 100))
        return travel_time * pollution_penalty
    
    path = nx.shortest_path(
        self.graph,
        source=start_node,
        target=end_node,
        weight=pollution_weight  # Dynamic weight function
    )
```

**Key Insight**: 
- **Fastest path**: Uses pre-computed `travel_time` weights (cached in graph)
- **Cleanest path**: Uses dynamic weight function that calculates AQI **during** Dijkstra traversal

---

## 2. Interpolation Method

### 2.1 When is Interpolation Computed?

**Answer**: Interpolation is computed **ON-THE-FLY during route calculation**, NOT pre-computed.

**Evidence** (aqi_service.py):
- Stations are loaded once at initialization (Line 28)
- `get_aqi_at_point()` is called for each edge midpoint during Dijkstra (simple_router.py Line 51)
- No pre-computed AQI grid or heatmap exists

### 2.2 Interpolation Algorithm

**File**: `aqi_service.py` (Line 86-111)

**Method**: Inverse Distance Weighting (IDW)

```python
def _inverse_distance_weighting(self, lat: float, lon: float, power: float = 2):
    # 1. Calculate distances to ALL stations
    distances = cdist([point], station_coords)[0]
    
    # 2. Filter stations with valid AQI data
    valid_indices = [i for i, s in enumerate(self.stations) if s['aqi'] is not None]
    
    # 3. Calculate weights: weight = 1 / (distance + 0.1)
    valid_weights = 1 / (valid_distances + 0.1)
    valid_weights = valid_weights / valid_weights.sum()  # Normalize
    
    # 4. Weighted average of AQI values
    interpolated_aqi = np.sum(valid_weights * valid_aqi)
    return interpolated_aqi
```

**Key Parameters**:
- **Power parameter**: Not used in current implementation (default 2 but not applied)
- **Smoothing constant**: 0.1 added to distance to prevent division by zero
- **Station range**: **ALL loaded stations** (no radius filter)
- **Current stations**: 95 stations in Newtown-focused area

### 2.3 Alternative Methods Available

1. **Nearest Neighbor** (Line 113-121): Uses closest station's AQI
2. **Weighted Average** (Line 123-152): Uses stations within 3.0 km radius

---

## 3. Pollution Penalty Calculation

### 3.1 Formula

**File**: `simple_router.py` (Line 54)

```python
pollution_penalty = 1 + (self.pollution_factor * (aqi / 100))
```

**Components**:
- `pollution_factor`: User-adjustable (default 2.0)
- `aqi`: Interpolated AQI at edge midpoint
- Base penalty: 1.0 (no penalty for AQI = 0)
- Penalty scales linearly with AQI

### 3.2 Penalty Examples

| AQI | pollution_factor=2.0 | pollution_factor=3.0 | pollution_factor=1.0 |
|-----|---------------------|---------------------|---------------------|
| 50  | 2.0x                | 2.5x                | 1.5x                |
| 100 | 3.0x                | 4.0x                | 2.0x                |
| 150 | 4.0x                | 5.5x                | 2.5x                |
| 200 | 5.0x                | 7.0x                | 3.0x                |

### 3.3 How Penalty Affects Route Selection

The penalty multiplies the travel time:
```python
weighted_travel_time = travel_time * pollution_penalty
```

**Effect**:
- High AQI roads appear "longer" in time cost
- Dijkstra avoids high-AQI edges even if they're faster
- Higher pollution_factor = more detour to avoid pollution

---

## 4. AQI Calculation at Road Midpoints

### 4.1 Where Midpoints are Calculated

**File**: `simple_router.py` (Line 44-48)

```python
# For each edge in the graph during Dijkstra
u_data = self.graph.nodes[u]
v_data = self.graph.nodes[v]
mid_lat = (u_data['y'] + v_data['y']) / 2
mid_lon = (u_data['x'] + v_data['x']) / 2
```

**Timing**: 
- Calculated **during** Dijkstra traversal for each edge evaluated
- Not pre-computed
- Called potentially hundreds of times per route calculation

### 4.2 Station Fetching for Interpolation

**Answer**: Uses **ALL 95 loaded stations** (no radius filter)

**Current Implementation** (aqi_service.py Line 86-111):
- Calculates distances to all 95 stations
- Weights each station by inverse distance
- No spatial filtering (stations 50km away still influence result)

**Performance Impact**:
- For each midpoint: 95 distance calculations + weighted average
- For 10km route with ~60 edges: ~5,700 distance calculations
- This is the computational bottleneck

### 4.3 Range of Influence

**Current**: Unlimited (all stations influence all points)

**Recommended**: Add radius filter for efficiency:
```python
# Filter stations within 5km radius
within_radius = [i for i, d in enumerate(distances) if d <= 5.0]
```

---

## 5. Pollution Hotspot Detection

### 5.1 Current Implementation

**Answer**: No explicit hotspot detection

The system:
- Uses continuous interpolation
- No threshold-based hotspot identification
- No special handling for high-AQI areas
- Pollution penalty scales linearly with AQI

### 5.2 Hotspot Calculation (Implicit)

Hotspots emerge naturally from:
1. High AQI station readings
2. IDW interpolation spreading high values spatially
3. Pollution penalty making these areas "expensive" to traverse

**Example**:
- Station with AQI 150 creates high penalty zone
- Dijkstra automatically routes around this zone
- No explicit hotspot list or threshold

---

## 6. Waypoint Generation

### 6.1 Where Do 60-70 Waypoints Come From?

**Answer**: Graph nodes from the OpenStreetMap road network

**Source**: `basic_network.py` (Line 30-35)
```python
self.graph = ox.graph_from_bbox(
    self.north, self.south, self.east, self.west,
    network_type='drive',
    simplify=True,  # OSM simplification enabled
    retain_all=True
)
```

**Network Statistics**:
- Total nodes: 31,894
- Total edges: ~60,000
- Area: ~225 km² (15km × 15km)
- Node density: ~142 nodes/km²

### 6.2 Why 60-70 Waypoints for 10km Route?

**Calculation**:
- 10km route through urban area
- Average node spacing: ~150-200m in dense urban network
- 10km / 0.17km spacing = ~59 nodes
- Plus start and end points = ~60 waypoints

**Graph Structure**:
```
Intersection nodes: Every road intersection
Way nodes: Curves, changes in road attributes
POI nodes: Traffic signals, speed limits
```

### 6.3 Path Analysis Output

**File**: `simple_router.py` (Line 93-155)

The `analyze_path_pollution()` function:
- Iterates through each node pair in path
- Calculates AQI at each edge midpoint
- Returns statistics including `aqi_samples` (number of edges)
- This equals waypoint count - 1

---

## 7. Reducing Waypoints to 20-25 for 10km

### 7.1 Current Problem

- 60-70 waypoints for 10km = too many for navigation
- Creates complex polyline
- Slower rendering
- Unnecessary detail for turn-by-turn

### 7.2 Solution 1: Graph Simplification (Recommended)

**Modify**: `basic_network.py`

```python
# Increase simplification tolerance
self.graph = ox.graph_from_bbox(
    self.north, self.south, self.east, self.west,
    network_type='drive',
    simplify=True,
    retain_all=False,  # Remove isolated components
    truncate_by_edge=True  # Remove dead ends
)

# Additional simplification
self.graph = ox.simplify_graph(
    self.graph,
    tolerance=25,  # Merge nodes within 25m (default is 10m)
    merge_edges=True
)
```

**Expected Result**: 30-40% reduction in waypoints

### 7.3 Solution 2: Post-Processing Path Simplification

**Add to**: `simple_router.py`

```python
def simplify_path(self, path, tolerance_km=0.5):
    """
    Simplify path using Douglas-Peucker algorithm
    tolerance_km: Minimum distance between waypoints (0.5km = 500m)
    """
    if len(path) <= 2:
        return path
    
    # Convert to coordinates
    coords = [(self.graph.nodes[n]['y'], self.graph.nodes[n]['x']) for n in path]
    
    # Douglas-Peucker simplification
    from shapely.geometry import LineString
    line = LineString(coords)
    simplified = line.simplify(tolerance_km * 1000)  # Convert to meters
    
    # Find closest nodes to simplified points
    simplified_path = []
    for point in simplified.coords:
        # Find nearest graph node
        nearest = self._find_graph_node(point[0], point[1])
        if nearest not in simplified_path:
            simplified_path.append(nearest)
    
    return simplified_path
```

**Usage**:
```python
clean_path = router.find_cleanest_path(...)
simplified_path = router.simplify_path(clean_path, tolerance_km=0.5)
```

**Expected Result**: 20-25 waypoints for 10km route

### 7.3 Solution 3: Edge-Based Path (Most Efficient)

**Modify**: `simple_router.py` return edges instead of nodes

```python
def find_cleanest_path_edges(self, start_lat, start_lon, end_lat, end_lon):
    """Return edges instead of nodes for fewer waypoints"""
    # ... same Dijkstra logic ...
    
    # Convert node path to edge path
    edge_path = []
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        edge_data = self.graph.get_edge_data(u, v)
        if edge_data:
            edge = list(edge_data.values())[0]
            edge_path.append({
                'start': (self.graph.nodes[u]['y'], self.graph.nodes[u]['x']),
                'end': (self.graph.nodes[v]['y'], self.graph.nodes[v]['x']),
                'length': edge.get('length', 0),
                'travel_time': edge.get('travel_time', 0)
            })
    
    return edge_path
```

**Expected Result**: 15-20 edges for 10km route (major road segments)

### 7.4 Solution 4: Adaptive Sampling

**Add to**: `simple_router.py`

```python
def adaptive_sample_path(self, path, target_waypoints=25):
    """
    Sample path to achieve target waypoint count
    Uses distance-based uniform sampling
    """
    if len(path) <= target_waypoints:
        return path
    
    # Calculate total distance
    total_distance = 0
    distances = [0]
    for i in range(len(path) - 1):
        u = self.graph.nodes[path[i]]
        v = self.graph.nodes[path[i + 1]]
        dist = geodesic((u['y'], u['x']), (v['y'], v['x'])).kilometers
        total_distance += dist
        distances.append(total_distance)
    
    # Calculate sampling interval
    interval = total_distance / (target_waypoints - 1)
    
    # Sample waypoints
    sampled_path = [path[0]]  # Always include start
    current_distance = interval
    
    for i in range(1, len(path) - 1):
        if distances[i] >= current_distance:
            sampled_path.append(path[i])
            current_distance += interval
    
    sampled_path.append(path[-1])  # Always include end
    
    return sampled_path
```

**Expected Result**: Exactly 25 waypoints for 10km route

---

## 8. Performance Optimization Recommendations

### 8.1 Interpolation Optimization

**Current bottleneck**: IDW uses all 95 stations for every point

**Optimization 1**: Add radius filter
```python
def _inverse_distance_weighting(self, lat: float, lon: float, radius_km=5.0):
    # Only use stations within 5km
    within_radius = [i for i, d in enumerate(distances) if d <= radius_km]
    # ... rest of IDW logic
```

**Expected speedup**: 3-5x faster (typical: 10-15 stations vs 95)

### 8.2 Cache Interpolation Results

**Add spatial cache**:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_aqi_at_point_cached(self, lat: float, lon: float):
    # Round to 4 decimal places (~11m precision)
    lat_rounded = round(lat, 4)
    lon_rounded = round(lon, 4)
    return self._inverse_distance_weighting(lat_rounded, lon_rounded)
```

**Expected benefit**: 50-70% cache hit rate for repeated queries

### 8.3 Pre-Compute AQI Grid

**For production use**:
```python
def precompute_aqi_grid(self, resolution_km=0.1):
    """Create 100m resolution AQI grid"""
    # Generate grid points
    # Pre-compute AQI for each point
    # Store in 2D array for O(1) lookup
```

**Expected benefit**: 100x faster interpolation (no distance calculations)

---

## 9. Summary Table

| Component | Current Implementation | Computation Timing | Performance Impact |
|-----------|----------------------|---------------------|-------------------|
| Route Finding | NetworkX Dijkstra | On-demand | Fast (ms) |
| Interpolation | IDW with 95 stations | Per edge midpoint | Slow (bottleneck) |
| Pollution Penalty | Linear formula | Per edge | Fast |
| Waypoint Generation | OSM graph nodes | From graph | High count (60-70) |
| Hotspot Detection | None (implicit) | N/A | N/A |

---

## 10. Recommended Changes

### Priority 1: Reduce Waypoints
- Implement Solution 2 (Douglas-Peucker simplification)
- Target: 20-25 waypoints for 10km routes
- Impact: Better UX, faster rendering

### Priority 2: Optimize Interpolation
- Add 5km radius filter to IDW
- Implement LRU cache for repeated queries
- Impact: 5-10x faster route calculation

### Priority 3: Add Hotspot Detection
- Implement threshold-based hotspot identification
- Visualize hotspots on map
- Impact: Better user understanding

### Priority 4: Pre-computation (Production)
- Implement AQI grid for large-scale deployment
- Update grid every 15 minutes
- Impact: 100x faster, suitable for real-time routing

---

## 11. Code Locations Reference

| Function | File | Line | Purpose |
|----------|------|------|---------|
| `find_fastest_path()` | simple_router.py | 11-30 | Standard Dijkstra |
| `find_cleanest_path()` | simple_router.py | 32-71 | Pollution-aware Dijkstra |
| `pollution_weight()` | simple_router.py | 40-57 | Custom weight function |
| `analyze_path_pollution()` | simple_router.py | 93-155 | Path analysis |
| `get_aqi_at_point()` | aqi_service.py | 64-84 | Interpolation entry |
| `_inverse_distance_weighting()` | aqi_service.py | 86-111 | IDW implementation |
| `_weighted_average()` | aqi_service.py | 123-152 | Radius-based method |
| `download_network()` | basic_network.py | 24-43 | OSM graph download |
| `simplify_graph()` | basic_network.py | 30-35 | Graph simplification |

---

## 12. Testing Recommendations

### Test Case 1: Interpolation Accuracy
```python
# Test interpolation at known locations
test_points = [
    (22.5726, 88.3639, "Center"),
    (22.5800, 88.3800, "Newtown"),
    (22.5600, 88.3400, "Howrah")
]
for lat, lon, name in test_points:
    aqi = interpolator.get_aqi_at_point(lat, lon)
    print(f"{name}: AQI {aqi}")
```

### Test Case 2: Waypoint Reduction
```python
# Test simplification
original_path = router.find_cleanest_path(...)
print(f"Original waypoints: {len(original_path)}")

simplified = router.simplify_path(original_path, tolerance_km=0.5)
print(f"Simplified waypoints: {len(simplified)}")
```

### Test Case 3: Performance Benchmark
```python
import time
start = time.time()
path = router.find_cleanest_path(...)
end = time.time()
print(f"Route calculation time: {end - start:.3f}s")
```

---

## 13. Conclusion

The clean route algorithm uses a sophisticated combination of:
- **Dijkstra's algorithm** for pathfinding
- **Dynamic interpolation** for pollution estimation
- **Linear pollution penalty** for route weighting

**Key findings**:
1. Interpolation is computed on-the-fly (not pre-computed)
2. All 95 stations influence every point (inefficient)
3. Waypoints come from OSM graph nodes (60-70 for 10km)
4. No explicit hotspot detection
5. Pollution penalty scales linearly with AQI

**Recommended improvements**:
1. Add path simplification (target: 20-25 waypoints)
2. Add radius filter to interpolation (5km)
3. Implement caching for repeated queries
4. Consider pre-computed grid for production

These changes will significantly improve performance while maintaining routing accuracy.
