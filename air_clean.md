# Clean Air Path Implementation

This document focuses specifically on the clean air (low air pollution exposure) routing algorithm and implementation.

---

## Overview

The clean air path routing finds routes with minimal exposure to air pollution by:
1. Using **raster-based AQI data** (NOT discrete monitoring stations)
2. Sampling AQI values at road edge center points
3. Calculating pollution-weighted edge costs
4. Running Dijkstra's algorithm with pollution-adjusted weights

---

## Key Difference: Raster vs Station-Based

### This Implementation (Green Path Server)

```
┌─────────────────────────────────────────┐
│  Raster-based AQI Data (Grid)           │
│  ┌───┬───┬───┬───┬───┐                 │
│  │ 1.2│ 1.5│ 2.1│ 1.8│ 1.3│            │
│  ├───┼───┼───┼───┼───┤                 │
│  │ 1.4│ 1.7│ 2.3│ 1.9│ 1.4│            │
│  ├───┼───┼───┼───┼───┤                 │
│  │ 1.3│ 1.6│ 2.0│ 1.7│ 1.2│            │
│  └───┴───┴───┴───┴───┘                 │
└─────────────────────────────────────────┘
              ↓ Sample at edge centers
┌─────────────────────────────────────────┐
│  Road Graph Edges with AQI Values       │
│  Edge 1: AQI = 1.5                      │
│  Edge 2: AQI = 1.8                      │
│  Edge 3: AQI = 2.1                      │
└─────────────────────────────────────────┘
```

### Station-Based Approach (e.g., Kolkata)

```
┌─────────────────────────────────────────┐
│  Discrete AQI Monitoring Stations       │
│  ● Station A: AQI = 67                 │
│  ● Station B: AQI = 45                 │
│  ● Station C: AQI = 156                │
└─────────────────────────────────────────┘
              ↓ Interpolate (IDW/Kriging)
┌─────────────────────────────────────────┐
│  Road Graph Edges with AQI Values       │
│  Edge 1: AQI = 55 (interpolated)       │
│  Edge 2: AQI = 62 (interpolated)       │
│  Edge 3: AQI = 89 (interpolated)       │
└─────────────────────────────────────────┘
```

**This implementation uses raster-based sampling, NOT station interpolation.**

---

## Clean Air Routing Pipeline

```
1. AQI Data Acquisition
   ↓
   NetCDF file from air quality model/satellite
   ↓
2. Raster Processing
   ↓
   Convert NetCDF → GeoTIFF
   Apply scale/offset corrections
   Fill nodata values with interpolation
   ↓
3. Spatial Sampling
   ↓
   Sample AQI at edge center points from raster
   Assign AQI values to graph edges
   ↓
4. Cost Calculation
   ↓
   Calculate AQI coefficient for each edge
   Apply sensitivity coefficients
   Generate weighted edge costs
   ↓
5. Route Finding
   ↓
   Run Dijkstra with pollution-weighted costs
   Generate multiple routes with different sensitivities
   ↓
6. Exposure Analysis
   ↓
   Calculate AQI class exposures
   Compute mean AQI
   Compare to fastest route
```

---

## Algorithm Details

### Step 1: AQI Data Processing

**Location:** `src/aqi_updater/aq_processing.py`

#### NetCDF to GeoTIFF Conversion

```python
def convert_aq_nc_to_tif(dir: str, aqi_nc_name: str) -> str:
    """Converts netCDF file to georeferenced raster file."""
    data = xarray.open_dataset(dir + aqi_nc_name)
    aqi = data['AQI']  # Automatically scaled and offset
    aqi = aqi.rio.set_crs('epsg:4326')
    
    aqi_date_str = aqi_nc_name[:-3][-13:]
    aqi_tif_name = f'aqi_{aqi_date_str}.tif'
    aqi.rio.to_raster(fr'{dir}{aqi_tif_name}')
    return aqi_tif_name
```

**Data Source:** Air quality model output or satellite-derived AQI data in NetCDF format

**Key Points:**
- AQI values are automatically scaled and offset by xarray
- CRS is set to WGS84 (EPSG:4326)
- Output is a GeoTIFF raster

#### Scale/Offset Correction

```python
def fix_aqi_tiff_scale_offset(aqi_filepath: str) -> bool:
    """Applies scale and offset to unscaled raster values."""
    aqi_raster = rasterio.open(aqi_filepath)
    aqi_band = aqi_raster.read(1)
    
    scale = aqi_raster.scales[0]
    offset = aqi_raster.offsets[0]
    aqi_band = aqi_band * scale + offset
    
    # Write corrected raster
    # ... (write back to file)
```

**Formula:**
$$
\text{AQI}_{\text{corrected}} = \text{AQI}_{\text{raw}} \times \text{scale} + \text{offset}
$$

#### Nodata Filling

```python
def fillna_in_raster(dir: str, aqi_tif_name: str, na_val: float = 1.0) -> bool:
    """Fills nodata values by interpolating from surrounding cells."""
    aqi_raster = rasterio.open(aqi_filepath)
    aqi_band = aqi_raster.read(1)
    
    # Create nodata mask
    aqi_nodata_mask = np.where(aqi_band <= na_threshold, 0, aqi_band)
    aqi_band_fillna = fill.fillnodata(aqi_band, mask=aqi_nodata_mask)
    
    # Write filled raster
    # ... (write back to file)
```

**Method:** Rasterio's `fillnodata` - inverse distance weighted interpolation

---

### Step 2: Spatial Sampling to Graph Edges

**Location:** `src/aqi_updater/aq_sampling.py`

#### Create Sampling Points

```python
def get_sampling_point_gdf_from_graph(graph) -> GeoDataFrame:
    """Creates GeoDataFrame of edges with center point geometries."""
    edge_gdf = ig_utils.get_edge_gdf(graph, attrs=[E.id_ig, E.id_way], geom_attr=E.geom_wgs)
    
    # Filter out edges with null geometry
    edge_gdf = edge_gdf[edge_gdf[E.geom_wgs.name].apply(lambda x: isinstance(x, LineString))]
    
    # Add point geometries at edge centers
    edge_gdf['point_geom'] = [
        geom.interpolate(0.5, normalized=True)
        for geom in edge_gdf[E.geom_wgs.name]
    ]
    return edge_gdf
```

**Strategy:** Sample at 50% (midpoint) of each edge

#### Sample AQI Values

```python
def sample_aq_to_point_gdf(
    sampling_gdf: GeoDataFrame,
    aq_tif_file: str,
    aq_attr_name: str
) -> GeoDataFrame:
    """Joins AQI values from raster to edges by spatial sampling."""
    gdf = sampling_gdf.copy()
    aqi_raster = rasterio.open(aq_tif_file)
    
    # Get edge center coordinates
    coords = [
        (x, y) for x, y
        in zip(
            [point.x for point in gdf['point_geom']],
            [point.y for point in gdf['point_geom']]
        )
    ]
    coords = round_coordinates(coords)
    
    # Sample AQI at coordinates using bilinear interpolation
    gdf[aq_attr_name] = [round(x.item(), 2) for x in aqi_raster.sample(coords)]
    return gdf
```

**Method:** Bilinear interpolation from rasterio

**Output:** Each edge gets an AQI value sampled at its center

---

### Step 3: AQI Cost Calculation

**Location:** `src/gp_server/app/aq_exposures.py`

#### AQI Coefficient

```python
def get_aqi_coeff(aqi: float) -> float:
    """Returns cost coefficient for AQI based costs."""
    if aqi < 0.95:
        raise InvalidAqiException(f'Received invalid AQI value: {aqi}')
    elif aqi < 1.0:
        return 0
    else:
        return (aqi - 1) / 4
```

**Formula:**
$$
\text{AQI}_{\text{coeff}} = \frac{\text{AQI} - 1}{4}
$$

**Range:** 0 to 1 (for AQI 1.0 to 5.0)

#### Edge Cost Calculation

```python
def calc_aqi_cost(
    length: float,
    aqi_coeff: float,
    bike_time_cost: float = None,
    sensitivity: float = 1.0
) -> float:
    """Returns AQI based cost based on exposure to certain AQI."""
    base_cost = length if not bike_time_cost else bike_time_cost
    return round(base_cost + base_cost * aqi_coeff * sensitivity, 2)
```

**Cost Formula:**
$$
\text{Cost} = \text{BaseCost} \times (1 + \text{AQI}_{\text{coeff}} \times \text{sensitivity})
$$

**Where:**
- `BaseCost` = length (walking) or bike_time_cost (biking)
- `sensitivity` = user-defined coefficient (0-40)

#### Generate Multiple Sensitivity Costs

```python
def get_aqi_costs(
    aqi: float,
    length: float,
    sensitivities: List[float],
    bike_time_cost: float = None,
    travel_mode: TravelMode = TravelMode.WALK
) -> Dict[str, float]:
    """Returns a set of AQI based costs for different sensitivities."""
    try:
        aqi_coeff = get_aqi_coeff(aqi)
    except InvalidAqiException:
        # Assign high costs to edges without AQI data
        aqi_coeff = 10
    
    cost_prefix = cost_prefix_dict[travel_mode][RoutingMode.CLEAN]
    aq_costs = {
        f'{cost_prefix}{sen}': calc_aqi_cost(
            length,
            aqi_coeff,
            bike_time_cost=bike_time_cost,
            sensitivity=sen
        )
        for sen in sensitivities
    }
    return aq_costs
```

**Sensitivity Values:**
- Walking: `[0, 5, 10, 15, 20]`
- Biking: `[0, 10, 20, 30, 40]`

**Invalid AQI Handling:** Coefficient = 10 (very high cost to avoid edge)

---

### Step 4: Route Finding

**Location:** `src/gp_server/app/routing.py`

#### Generate Clean Routes

```python
def __find_exp_optimized_paths(G: GraphHandler, od_settings: OdSettings, od_nodes: OdData):
    cost_prefix = cost_prefix_dict[od_settings.travel_mode][od_settings.routing_mode]
    return [
        Path(
            path_id=f'{cost_prefix}{sen}',
            path_type=path_type_by_routing_mode[od_settings.routing_mode],
            edge_ids=G.get_least_cost_path(
                od_nodes.orig_node.id,
                od_nodes.dest_node.id,
                weight=f'{cost_prefix}{sen}'
            ),
            cost_coeff=sen
        )
        for sen in od_settings.sensitivities
    ]
```

**Algorithm:** Dijkstra's shortest path with pollution-weighted edge costs

**Output:** Multiple routes with different pollution sensitivities

---

### Step 5: Exposure Analysis

**Location:** `src/gp_server/app/aq_exposures.py`

#### AQI Class Calculation

```python
def get_aqi_class(aqi: float) -> int:
    """Returns AQI class identifier (1-9)."""
    return floor(aqi * 2) - 1 if np.isfinite(aqi) else 0
```

**Class Ranges:**
- Class 1: AQI 1.0-1.5
- Class 2: AQI 1.5-2.0
- Class 3: AQI 2.0-2.5
- ...
- Class 9: AQI 4.5-5.0+

#### Aggregate AQI Class Exposures

```python
def aggregate_aqi_class_exps(aqi_exp_list: List[Tuple[float, float]]) -> Dict[int, float]:
    """Returns aggregated exposures to different AQI classes."""
    aqi_cl_exps = defaultdict(float)
    
    for aqi, length in aqi_exp_list:
        aqi_cl_exps[get_aqi_class(aqi)] += length
    
    return {
        aqi_class: round(length, 3)
        for aqi_class, length in aqi_cl_exps.items()
    }
```

**Example Output:**
```json
{
  "aqi_cl_exps": {
    "1": 305.4,
    "2": 205.1,
    "3": 50.4
  }
}
```

Meaning: 305.4m in class 1, 205.1m in class 2, etc.

#### Mean AQI Calculation

```python
def get_mean_aqi(aqi_exp_list: List[Tuple[float, float]]) -> float:
    """Calculates mean aqi from list of (aqi, distance) tuples."""
    total_dist = sum([aqi_exp[1] for aqi_exp in aqi_exp_list])
    total_aqi = sum([aqi_exp[0] * aqi_exp[1] for aqi_exp in aqi_exp_list])
    return round(total_aqi/total_dist, 2)
```

**Formula:**
$$
\text{Mean AQI} = \frac{\sum (\text{AQI}_i \times \text{distance}_i)}{\sum \text{distance}_i}
$$

---

## Route Comparison Metrics

Each clean route includes the following metrics for comparison with the fastest route:

| Metric | Description | Formula |
|--------|-------------|---------|
| `aqc` | Air pollution cost | $\sum (\text{length}_i \times \text{AQI}_{\text{coeff},i})$ |
| `aqi_m` | Mean AQI | Weighted average of edge AQI values |
| `aqc_norm` | Normalized AQI cost | $\frac{\text{aqc}}{\text{length}}$ |
| `len_diff` | Extra distance vs fastest | $\text{clean\_length} - \text{fastest\_length}$ |
| `len_diff_pct` | Extra distance percentage | $\frac{\text{len\_diff}}{\text{fastest\_length}} \times 100$ |
| `aqi_cl_exps` | AQI class exposures | Distance per AQI class |

---

## Clean API Endpoint

**Format:**
```
/paths/{travel_mode}/clean/{orig_coords}/{dest_coords}
```

**Example:**
```
/paths/walk/clean/60.20772,24.96716/60.2037,24.9653
```

**Response Structure:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "id": "fast",
        "type": "fast",
        "length": 1250.5,
        "aqc": 450.2,
        "aqi_m": 1.8,
        "aqc_norm": 0.36,
        "len_diff": 0,
        "len_diff_pct": 0
      },
      "geometry": {...}
    },
    {
      "type": "Feature",
      "properties": {
        "id": "clean_5",
        "type": "clean",
        "length": 1320.3,
        "aqc": 320.5,
        "aqi_m": 1.5,
        "aqc_norm": 0.24,
        "len_diff": 69.8,
        "len_diff_pct": 5.6
      },
      "geometry": {...}
    },
    {
      "type": "Feature",
      "properties": {
        "id": "clean_10",
        "type": "clean",
        "length": 1385.7,
        "aqc": 280.3,
        "aqi_m": 1.4,
        "aqc_norm": 0.20,
        "len_diff": 135.2,
        "len_diff_pct": 10.8
      },
      "geometry": {...}
    }
  ]
}
```

---

## Implementation for Kolkata: Required Changes

To adapt this for Kolkata with station-based AQI data:

### Current (Raster-Based)
```
NetCDF → GeoTIFF → Sample at edge centers → Edge AQI values
```

### Required for Kolkata (Station-Based)
```
Station API → Station locations → IDW/Kriging interpolation → Edge AQI values
```

### Key Changes Needed

1. **Data Source:**
   - Replace NetCDF raster with station API (CPCB, WAQI, OpenAQ)
   - Fetch station locations and AQI values

2. **Interpolation:**
   - Implement IDW (Inverse Distance Weighting) or Kriging
   - Interpolate AQI values to all edge center points

3. **Edge Assignment:**
   - Same sampling point approach (edge centers)
   - Use interpolated values instead of raster sampling

4. **Update Frequency:**
   - Raster: Typically hourly/daily model updates
   - Stations: Can be real-time (every 15-30 minutes)

### Pseudocode for Station-Based Approach

```python
def interpolate_aqi_to_edges(edges, stations):
    """Interpolate AQI from stations to edge centers using IDW."""
    edge_aqi_values = {}
    
    for edge in edges:
        edge_center = get_edge_center(edge)
        
        # Find k nearest stations
        nearest_stations = find_k_nearest_stations(
            edge_center, 
            stations, 
            k=5
        )
        
        # Calculate IDW weighted average
        weights = []
        aqi_values = []
        
        for station in nearest_stations:
            distance = haversine_distance(
                edge_center.lat, edge_center.lon,
                station.lat, station.lon
            )
            weight = 1.0 / (distance ** 2)
            weights.append(weight)
            aqi_values.append(station.aqi)
        
        # IDW formula
        total_weight = sum(weights)
        interpolated_aqi = sum(w * aqi for w, aqi in zip(weights, aqi_values)) / total_weight
        
        edge_aqi_values[edge.id] = interpolated_aqi
    
    return edge_aqi_values
```

---

## Summary

### Current Implementation
- **Data Source:** Raster (NetCDF/GeoTIFF) from air quality models
- **Method:** Spatial sampling at edge centers
- **Interpolation:** Bilinear interpolation from raster
- **Update Frequency:** Model-dependent (hourly to daily)

### For Kolkata Adaptation
- **Data Source:** Discrete monitoring stations (CPCB, WAQI, OpenAQ)
- **Method:** IDW/Kriging interpolation from stations
- **Interpolation:** Distance-weighted averaging
- **Update Frequency:** Real-time (15-30 minutes)

### Core Algorithm (Same for Both)
1. Assign AQI values to graph edges
2. Calculate pollution-weighted edge costs
3. Run Dijkstra with weighted costs
4. Compute exposure metrics
5. Compare with fastest route

---

**Document Version:** 1.0  
**Last Updated:** May 11, 2026
