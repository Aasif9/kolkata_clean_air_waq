# Algorithms Used in Green Path Server

This document provides a comprehensive overview of all algorithms implemented in the Green Path Server project for environment-aware routing.

---

## Table of Contents

1. [Routing Algorithms](#1-routing-algorithms)
2. [Spatial & Geometric Algorithms](#2-spatial--geometric-algorithms)
3. [Environmental Cost Algorithms](#3-environmental-cost-algorithms)
4. [Exposure Aggregation Algorithms](#4-exposure-aggregation-algorithms)
5. [Biking Cost Algorithms](#5-biking-cost-algorithms)
6. [AQI Processing Algorithms](#6-aqi-processing-algorithms)
7. [Path Processing Algorithms](#7-path-processing-algorithms)
8. [Graph I/O Algorithms](#8-graph-io-algorithms)

---

## 1. Routing Algorithms

### 1.1 Dijkstra's Shortest Path

**Location:** `src/gp_server/app/graph_handler.py`

**Purpose:** Find the least cost path between two nodes in the graph using Dijkstra's algorithm.

**Implementation:**
```python
def get_least_cost_path(
    self,
    orig_node: int,
    dest_node: int,
    weight: str = 'length'
) -> List[int]:
    """Calculates a least cost path by the given edge weight."""
    s_path = self.graph.get_shortest_paths(
        orig_node,
        to=dest_node,
        weights=weight,
        mode=1,
        output='epath'
    )
    return s_path[0]
```

**Time Complexity:** $O((V + E) \log V)$ where V = vertices, E = edges

**Space Complexity:** $O(V)$

**Used For:**
- Fastest route calculation (weight = `length` or `bike_time_cost`)
- Safest route calculation (weight = `bike_safety_cost`)
- Clean route calculation (weight = `clean_cost_coeff`)
- Quiet route calculation (weight = `quiet_cost_coeff`)
- Green route calculation (weight = `green_cost_coeff`)

---

### 1.2 Multi-Criteria Weighted Shortest Path

**Location:** `src/gp_server/app/routing.py`

**Purpose:** Generate multiple routes with different optimization criteria by applying varying environmental sensitivity coefficients.

**Algorithm:**
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

**Key Concept:** Different sensitivity coefficients (`cost_coeff`) produce different routes:
- Higher sensitivity = stronger preference for environmental optimization
- Lower sensitivity = closer to fastest route

**Example Sensitivity Values:**
- Walking AQI sensitivities: `[0, 5, 10, 15, 20]`
- Biking AQI sensitivities: `[0, 10, 20, 30, 40]`
- Greenery sensitivities: `[0, 5, 10, 15, 20]`
- Noise sensitivities: `[0, 10, 20, 30, 40]`

---

## 2. Spatial & Geometric Algorithms

### 2.1 Coordinate Projection (CRS Transformation)

**Location:** `src/common/geometry.py`

**Purpose:** Transform coordinates between different coordinate reference systems.

**Implementation:**
```python
def project_geom(geom, geom_epsg: int = 4326, to_epsg: int = gp_conf.proj_crs_epsg):
    """Projects Shapely geometry to another CRS."""
    project = __projections[(geom_epsg, to_epsg)]
    return transform(project.transform, geom)
```

**Transformations:**
- WGS84 (EPSG:4326) → Projected CRS (EPSG:3879 for Finland)
- Projected CRS (EPSG:3879) → WGS84 (EPSG:4326)

**Library:** `pyproj`

---

### 2.2 Nearest Point on Line

**Location:** `src/gp_server/app/od_handler.py`

**Purpose:** Find the closest point on a line segment to a given point.

**Algorithm:**
```python
def __get_closest_point_on_line(line: LineString, point: Point) -> Point:
    """Finds the closest point on a line to given point."""
    projected = line.project(point)
    closest_point = line.interpolate(projected)
    return closest_point
```

**Time Complexity:** $O(n)$ where n = number of vertices in line

**Used For:** Snapping origin/destination points to road network edges

---

### 2.3 Line Splitting at Point

**Location:** `src/common/geometry.py`

**Purpose:** Split a line segment at a specific point.

**Algorithm:**
```python
def split_line_at_point(
    line: LineString,
    split_point: Point,
    tolerance: float = 0.01
) -> List[LineString]:
    """Splits a line at nearest intersecting point."""
    for snap_dist in (tolerance, 0.001, 0.0001, 0.00001, 0.000001, 0.0000001, 0.00000001):
        snap_line = snap(line, split_point, snap_dist)
        split_lines = split(snap_line, split_point)
        if len(split_lines) > 1:
            break
    return split_lines[0], split_lines[1]
```

**Strategy:** Iterative snapping with decreasing tolerance to handle precision issues

**Used For:** Creating temporary linking edges from origin/destination to graph

---

### 2.4 Nearest Node Search with Spatial Index

**Location:** `src/gp_server/app/graph_handler.py`

**Purpose:** Find the nearest graph node to a given point using spatial indexing.

**Algorithm:**
```python
def find_nearest_node(self, point: Point) -> Union[int, None]:
    """Finds the nearest node to a given point from the graph."""
    for radius in (50, 100) + (conf.max_od_search_dist_m,):
        possible_matches_index = list(
            self.__node_gdf.sindex.intersection(point.buffer(radius).bounds)
        )
        if possible_matches_index:
            break
    
    possible_matches = self.__node_gdf.iloc[possible_matches_index]
    points_union = possible_matches.geometry.unary_union
    nearest_geom = nearest_points(point, points_union)[1]
    nearest = possible_matches.geometry.geom_equals(nearest_geom)
    nearest_point = possible_matches.loc[nearest]
    return nearest_point.index.tolist()[0]
```

**Spatial Index:** R-tree (via GeoPandas `sindex`)

**Search Strategy:**
1. Incremental radius search: 50m → 100m → max_search_dist
2. Bounding box intersection for initial filtering
3. Exact distance calculation on filtered candidates

**Time Complexity:** $O(\log n)$ average for spatial index query

---

### 2.5 Nearest Edge Search with Spatial Index

**Location:** `src/gp_server/app/graph_handler.py`

**Purpose:** Find the nearest graph edge to a given point.

**Algorithm:**
```python
def find_nearest_edge(self, point: Point) -> Union[NearestEdge, None]:
    """Finds the nearest edge to a given point."""
    for radius in (35, 150, 400) + (conf.max_od_search_dist_m,):
        possible_matches_index = list(
            self.__edge_gdf.sindex.intersection(point.buffer(radius).bounds)
        )
        if possible_matches_index:
            possible_matches = self.__edge_gdf.iloc[possible_matches_index].copy()
            possible_matches['distance'] = [
                geom.distance(point) for geom in possible_matches[E.geometry.name]
            ]
            shortest_dist = possible_matches['distance'].min()
            if shortest_dist < radius:
                break
    
    nearest = possible_matches['distance'] == shortest_dist
    edge_id = possible_matches.loc[nearest].index[0]
    attrs = self.get_edge_attrs_by_id(edge_id)
    return NearestEdge(attrs, round(shortest_dist, 2))
```

**Search Strategy:**
1. Incremental radius search: 35m → 150m → 400m → max_search_dist
2. Bounding box intersection via R-tree
3. Euclidean distance calculation on candidates

**Time Complexity:** $O(\log n)$ average for spatial index query

---

## 3. Environmental Cost Algorithms

### 3.1 AQI Cost Calculation

**Location:** `src/gp_server/app/aq_exposures.py`

**Purpose:** Calculate edge cost based on Air Quality Index (AQI) exposure.

**AQI Coefficient Formula:**
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

**AQI Cost Formula:**
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

**Cost Function:**
$$
\text{Cost} = \text{BaseCost} \times (1 + \text{AQI}_{\text{coeff}} \times \text{sensitivity})
$$

**Where:**
- $\text{BaseCost} = \text{length}$ (walking) or $\text{bike\_time\_cost}$ (biking)
- $\text{AQI}_{\text{coeff}} = \frac{\text{AQI} - 1}{4}$
- $\text{sensitivity} = \text{user-defined coefficient (0-40)}$

**Invalid AQI Handling:**
- AQI < 0.95: Assign high cost coefficient (10) to avoid edge in routing

---

### 3.2 Noise Cost Calculation

**Location:** `src/gp_server/app/noise_exposures.py`

**Purpose:** Calculate edge cost based on noise exposure with logarithmic scaling.

**Noise Cost Coefficient (Version 3 - Logarithmic):**
```python
def calc_db_cost_v3(db) -> float:
    """Returns noise cost: every 10 dB increase doubles the cost."""
    if db <= 44:
        return 0.0
    db_cost = pow(10, (0.3 * db)/10)
    return round(db_cost / 100, 3)
```

**Formula:**
$$
\text{db\_cost} = \frac{10^{0.03 \times \text{db}}}{100}
$$

**Noise Cost Coefficient for Edge:**
```python
def get_noise_cost_coeff(noises: Dict[int, float], db_costs: Dict[int, float]) -> float:
    """Returns noise cost coefficient (weighted average)."""
    if not noises:
        return 0.0
    db_distance_cost = sum([db_costs[db] * length for db, length in noises.items()])
    total_length = sum(noises.values())
    return round(db_distance_cost / total_length, 3) if total_length else 0.0
```

**Noise-Adjusted Edge Cost:**
```python
def get_noise_adjusted_edge_cost(
    sensitivity: float,
    db_costs: Dict[int, float],
    noises: Union[dict, None],
    length: float,
    bike_time_cost: Union[float, None] = None
):
    """Returns composite edge cost: base_cost + noise_cost."""
    base_cost = bike_time_cost if bike_time_cost else length
    
    if noises is None:
        return round(base_cost + base_cost * 100 * sensitivity, 2)
    
    noise_cost_coeff = get_noise_cost_coeff(noises, db_costs)
    return round(base_cost + base_cost * noise_cost_coeff * sensitivity, 2)
```

**Cost Function:**
$$
\text{Cost} = \text{BaseCost} \times (1 + \text{NoiseCoeff} \times \text{sensitivity})
$$

**Noise Range Classification:**
- 40 dB: < 50 dB (quiet)
- 50 dB: 50-55 dB
- 55 dB: 55-60 dB
- 60 dB: 60-65 dB
- 65 dB: 65-70 dB
- 70 dB: ≥ 70 dB (loud)

---

### 3.3 Greenery (GVI) Cost Calculation

**Location:** `src/gp_server/app/greenery_exposures.py`

**Purpose:** Calculate edge cost based on Green View Index (GVI) to favor green routes.

**Greyness Index Concept:**
- Since Dijkstra requires non-negative costs and we want lower costs for higher GVI
- Use inverted concept: "greyness index" = 1 - GVI

**GVI-Adjusted Cost Formula:**
```python
def get_gvi_adjusted_cost(
    length: float,
    gvi: float,
    bike_time_cost: float = None,
    sensitivity: float = 1.0
) -> float:
    """Calculates GVI adjusted edge cost for GVI optimized routing."""
    base_cost = bike_time_cost if bike_time_cost else length
    return round(base_cost + (1 - gvi) * base_cost * sensitivity, 2)
```

**Cost Function:**
$$
\text{Cost} = \text{BaseCost} \times (1 + (1 - \text{GVI}) \times \text{sensitivity})
$$

**Where:**
- GVI = 0 (no greenery) → higher cost
- GVI = 1 (full greenery) → lower cost

**Assumptions:**
1. "Greyness index" = 1 - GVI
2. "Greyness cost" = (1 - GVI) × length
3. Base cost = length or bike_time_cost
4. GVI adjusted cost = base_cost + greyness cost × sensitivity

---

## 4. Exposure Aggregation Algorithms

### 4.1 AQI Class Exposure Aggregation

**Location:** `src/gp_server/app/aq_exposures.py`

**Purpose:** Aggregate route exposure by AQI class intervals.

**AQI Class Formula:**
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

**Aggregation Algorithm:**
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
```python
{1: 305.4, 2: 205.1, 3: 50.4}  # meters in each AQI class
```

---

### 4.2 Noise Range Exposure Aggregation

**Location:** `src/gp_server/app/noise_exposures.py`

**Purpose:** Aggregate route exposure by noise level ranges.

**Noise Range Classification:**
```python
def get_noise_range(db: float) -> int:
    """Returns lower limit of pre-defined dB range."""
    if db >= 70.0:
        return 70
    elif db >= 65.0:
        return 65
    elif db >= 60.0:
        return 60
    elif db >= 55.0:
        return 55
    elif db >= 50.0:
        return 50
    else:
        return 40
```

**Aggregation Algorithm:**
```python
def get_noise_range_exps(noises: dict, total_length: float) -> Dict[int, float]:
    """Calculates aggregated exposures to different noise level ranges."""
    db_range_lens = defaultdict(float)
    for db, exp in noises.items():
        db_range_lens[get_noise_range(db)] += exp
    
    return {
        k: round(v, 3)
        for k, v in db_range_lens.items()
    }
```

---

### 4.3 GVI Class Exposure Aggregation

**Location:** `src/gp_server/app/greenery_exposures.py`

**Purpose:** Aggregate route exposure by GVI class intervals.

**GVI Class Formula:**
```python
def get_gvi_class(gvi: float) -> int:
    """Classifies GVI to one of nine classes (1-10)."""
    if not isinstance(gvi, float) or gvi > 1 or gvi < 0:
        raise ValueError(f'GVI value is invalid: {gvi}')
    return ceil(gvi * 10)
```

**Class Ranges:**
- Class 1: GVI 0.0-0.1
- Class 2: GVI 0.1-0.2
- ...
- Class 10: GVI 0.9-1.0

**Aggregation Algorithm:**
```python
def aggregate_gvi_class_exps(gvi_exps: List[Tuple[float, float]]) -> Dict[int, float]:
    """Aggregates GVI exposures to nine 0.1 wide GVI ranges."""
    gvi_class_exps = defaultdict(float)
    
    for gvi, exp in gvi_exps:
        gvi_class_exps[get_gvi_class(gvi)] += exp
    
    return {
        gvi_class: round(exp, 3)
        for gvi_class, exp in gvi_class_exps.items()
    }
```

---

### 4.4 Weighted Mean Calculations

**Mean AQI:**
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

**Mean Noise Level:**
```python
def get_mean_noise_level(noises: dict, length: float) -> float:
    """Returns mean noise level weighted by contaminated distances."""
    sum_db = sum([(db + 2.5) * length for db, length in noises.items()])
    mean_db = sum_db/length
    return round(mean_db, 1)
```

**Formula:**
$$
\text{Mean dB} = \frac{\sum (\text{dB}_{\text{mid}} \times \text{distance}_i)}{\sum \text{distance}_i}$$

Where $\text{dB}_{\text{mid}} = \text{dB}_{\text{lower}} + 2.5$

**Mean GVI:**
```python
def get_mean_gvi(gvi_exps: List[Tuple[float, float]]) -> float:
    """Returns mean GVI by list of (gvi, length) tuples."""
    length = sum([length for _, length in gvi_exps])
    sum_gvi = sum([gvi * length for gvi, length in gvi_exps])
    return round(sum_gvi/length, 2)
```

---

### 4.5 Noise Exposure Index (NEI)

**Location:** `src/gp_server/app/noise_exposures.py`

**Purpose:** Calculate total noise exposure cost for a route.

**Algorithm:**
```python
def get_noise_exposure_index(
    noises: Dict[int, float],
    db_costs: Dict[int, float]
) -> float:
    """Returns total noise cost (noise exposure index)."""
    if not noises:
        return 0.0
    else:
        return round(sum([db_costs[db] * length for db, length in noises.items()]), 2)
```

**Formula:**
$$
\text{NEI} = \sum (\text{db\_cost}_i \times \text{distance}_i)
$$

---

## 5. Biking Cost Algorithms

### 5.1 Bikeability Classification

**Location:** `src/gp_server/app/edge_cost_factory_bike.py`

**Purpose:** Classify edges based on biking suitability.

**Classification Algorithm:**
```python
def get_bikeability(
    allows_biking: bool,
    is_stairs: bool
) -> Bikeability:
    if not allows_biking and is_stairs:
        return Bikeability.NO_BIKE_STAIRS
    if not allows_biking and not is_stairs:
        return Bikeability.NO_BIKE
    if allows_biking and is_stairs:
        return Bikeability.BIKE_OK_STAIRS
    if allows_biking:
        return Bikeability.BIKE_OK
```

**Bikeability Classes:**
- `NO_BIKE_STAIRS`: Stairs, biking not allowed
- `NO_BIKE`: No biking allowed
- `BIKE_OK_STAIRS`: Stairs, biking allowed
- `BIKE_OK`: Normal biking allowed

---

### 5.2 Bike Time Cost Calculation

**Location:** `src/gp_server/app/edge_cost_factory_bike.py`

**Purpose:** Calculate edge cost proportional to travel time.

**Algorithm:**
```python
def get_bike_cost(
    length: Union[float, None],
    bikeability: Bikeability,
    safety_factor: Union[float, None],
    bike_walk_time_ratio: float
) -> float:
    """Returns biking cost proportional to travel time."""
    if not length:
        return 0
    
    # normal stairs (NO_BIKE_STAIRS)
    if bikeability == Bikeability.NO_BIKE_STAIRS:
        return length * bike_walk_time_ratio * 15
    
    # no bike or bikeable stairs
    if bikeability == Bikeability.NO_BIKE or bikeability == Bikeability.BIKE_OK_STAIRS:
        return length * bike_walk_time_ratio * 1.2
    
    if safety_factor:
        return length * safety_factor
    
    return length
```

**Cost Formulas:**
- Normal stairs: $\text{cost} = \text{length} \times \frac{v_{\text{walk}}}{v_{\text{bike}}} \times 15$
- Walking with bike: $\text{cost} = \text{length} \times \frac{v_{\text{walk}}}{v_{\text{bike}}} \times 1.2$
- With safety factor: $\text{cost} = \text{length} \times \text{safety\_factor}$
- Normal biking: $\text{cost} = \text{length}$

---

### 5.3 Bike Safety Cost Calculation

**Purpose:** Calculate edge cost prioritizing safer routes.

**Algorithm:**
```python
graph.es[E.bike_safety_cost.value] = [
    round(
        get_bike_cost(
            length,
            bikeability,
            safety,
            bike_walk_time_ratio
        ), 1
    )
    for length, bikeability, safety
    in zip(
        graph.es[E.length.value],
        bikeabilities,
        graph.es[E.bike_safety_factor.value]
    )
]
```

**Safety Factor:** Typically ranges from 1.0 (safe) to higher values (less safe)

---

## 6. AQI Processing Algorithms

### 6.1 NetCDF to GeoTIFF Conversion

**Location:** `src/aqi_updater/aq_processing.py`

**Purpose:** Convert AQI data from NetCDF format to GeoTIFF raster format.

**Algorithm:**
```python
def convert_aq_nc_to_tif(dir: str, aqi_nc_name: str) -> str:
    """Converts netCDF file to georeferenced raster file."""
    data = xarray.open_dataset(dir + aqi_nc_name)
    aqi = data['AQI']
    aqi = aqi.rio.set_crs('epsg:4326')
    
    aqi_date_str = aqi_nc_name[:-3][-13:]
    aqi_tif_name = f'aqi_{aqi_date_str}.tif'
    aqi.rio.to_raster(fr'{dir}{aqi_tif_name}')
    return aqi_tif_name
```

**Libraries:** `xarray`, `rioxarray`

**Process:**
1. Open NetCDF file with xarray
2. Extract AQI layer (automatically scaled and offset)
3. Set CRS to WGS84 (EPSG:4326)
4. Export as GeoTIFF

---

### 6.2 Raster Scale/Offset Correction

**Location:** `src/aqi_updater/aq_processing.py`

**Purpose:** Apply scale and offset corrections to unscaled raster values.

**Algorithm:**
```python
def fix_aqi_tiff_scale_offset(aqi_filepath: str) -> bool:
    """Applies scale and offset to unscaled AQI raster values."""
    aqi_raster = rasterio.open(aqi_filepath)
    aqi_band = aqi_raster.read(1)
    
    if not _has_unscaled_aqi(aqi_raster):
        return False
    
    scale = _get_scale(aqi_raster)
    offset = _get_offset(aqi_raster)
    aqi_band = aqi_band * scale + offset
    
    # Write corrected raster
    aqi_raster_fillna = rasterio.open(
        aqi_filepath, 'w',
        driver='GTiff',
        height=aqi_raster.shape[0],
        width=aqi_raster.shape[1],
        count=1,
        dtype='float32',
        transform=aqi_raster.transform,
        crs=aqi_raster.crs
    )
    aqi_raster_fillna.write(aqi_band, 1)
    aqi_raster_fillna.close()
    return True
```

**Formula:**
$$
\text{AQI}_{\text{corrected}} = \text{AQI}_{\text{raw}} \times \text{scale} + \text{offset}
$$

---

### 6.3 Nodata Filling with Interpolation

**Location:** `src/aqi_updater/aq_processing.py`

**Purpose:** Fill missing (nodata) values in AQI raster using interpolation.

**Algorithm:**
```python
def fillna_in_raster(
    dir: str,
    aqi_tif_name: str,
    na_val: float = 1.0,
    log: Logger = None
) -> bool:
    """Fills nodata values by interpolating from surrounding cells."""
    aqi_raster = rasterio.open(aqi_filepath)
    aqi_band = aqi_raster.read(1)
    
    # Find appropriate nodata threshold
    na_offsets = [0.0, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12]
    na_thresholds = [na_val + offset for offset in na_offsets]
    
    for na_threshold in na_thresholds:
        nodata_count = np.sum(aqi_band <= na_threshold)
        if nodata_count > 180000:
            break
    
    # Fill nodata using interpolation
    aqi_nodata_mask = np.where(aqi_band <= na_threshold, 0, aqi_band)
    aqi_band_fillna = fill.fillnodata(aqi_band, mask=aqi_nodata_mask)
    
    # Write filled raster
    aqi_raster_fillna = rasterio.open(
        aqi_filepath, 'w',
        driver='GTiff',
        height=aqi_raster.shape[0],
        width=aqi_raster.shape[1],
        count=1,
        dtype='float32',
        transform=aqi_raster.transform,
        crs=aqi_raster.crs
    )
    aqi_raster_fillna.write(aqi_band_fillna, 1)
    aqi_raster_fillna.close()
    return True
```

**Library:** `rasterio.fill.fillnodata`

**Strategy:** Iterative threshold adjustment to handle conversion inaccuracies

---

### 6.4 Spatial Sampling from Raster to Points

**Location:** `src/aqi_updater/aq_sampling.py`

**Purpose:** Sample AQI values from raster at edge center points.

**Algorithm:**
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
    
    # Sample AQI at coordinates
    gdf[aq_attr_name] = [round(x.item(), 2) for x in aqi_raster.sample(coords)]
    return gdf
```

**Sampling Strategy:**
1. Create point geometries at edge centers (interpolate at 0.5)
2. Round coordinates to 6 decimal places
3. Use rasterio's `sample()` method for bilinear interpolation

---

### 6.5 AQI Validation

**Location:** `src/aqi_updater/aq_sampling.py`

**Purpose:** Validate sampled AQI values for correctness.

**Validation Rules:**
```python
class AqiValidity(Enum):
    OK = 0
    Missing = 1
    UnderOne = 2
    UnderZero = 3
    HigherThan5 = 4
    WrongType = 5

def validate_aqi_exp(aqi: Union[float, Any]) -> AqiValidity:
    if not isinstance(aqi, float):
        return AqiValidity.WrongType
    elif aqi < 0:
        return AqiValidity.UnderZero
    elif aqi == 0.0 or not np.isfinite(aqi):
        return AqiValidity.Missing
    elif aqi < 0.95:
        return AqiValidity.UnderOne
    elif aqi > 5.05:
        return AqiValidity.HigherThan5
    else:
        return AqiValidity.OK
```

**Valid Range:** 0.95 ≤ AQI ≤ 5.05

**Handling Invalid Values:** Replace with `np.nan`

---

## 7. Path Processing Algorithms

### 7.1 Path Deduplication

**Location:** `src/gp_server/app/path_set.py`

**Purpose:** Remove duplicate paths with identical edge sequences.

**Algorithm:**
```python
def set_unique_paths(self, paths: List[Path]) -> None:
    """Filters out duplicate paths by edge_ids."""
    filtered: List[Path] = []
    prev_edge_ids: List[int] = []
    for path in paths:
        if path.edge_ids != prev_edge_ids:
            filtered.append(path)
        prev_edge_ids = path.edge_ids
    self.paths = filtered
```

**Time Complexity:** $O(n)$ where n = number of paths

---

### 7.2 Path Filtering by Geometry Overlay

**Location:** `src/gp_server/app/path_set.py`

**Purpose:** Filter out paths with nearly identical geometries using buffer overlay.

**Algorithm:**
```python
def filter_out_unique_geom_paths(self, buffer_m=50) -> None:
    """Filters out paths with nearly similar geometries."""
    if len(self.paths) <= 1:
        return
    
    cost_attr = 'aqc_norm' if self.routing_mode == RoutingMode.CLEAN else 'nei_norm'
    keep_path_ids = path_overlay_filter.get_unique_paths_by_geom_overlay(
        self.log,
        self.paths,
        buffer_m=buffer_m,
        cost_attr=cost_attr
    )
    if keep_path_ids:
        self.filter_paths_by_ids(keep_path_ids)
```

**Strategy:** "Greenest wins policy" - when paths overlap, keep the one with better environmental score

**Buffer Distance:** 50 meters default

---

### 7.3 Bike Path Sorting

**Location:** `src/gp_server/app/path_set.py`

**Purpose:** Sort bike paths by length and remove paths that are shorter but slower.

**Sorting Algorithm:**
```python
def sort_bike_paths_by_length(self):
    """Sorts bike paths by length."""
    self.paths.sort(key=lambda p: getattr(p, 'length'))
```

**Filtering Slower Shorter Paths:**
```python
def drop_slower_shorter_bike_paths(self):
    """Drops shorter paths that are slower."""
    drop_path_ids = []
    for idx, path in enumerate(self.paths):
        if idx == 0:
            prev_id, prev_length, prev_bike_time = (
                path.path_id, path.length, path.bike_time_cost
            )
            continue
        if prev_length < path.length and prev_bike_time > path.bike_time_cost:
            drop_path_ids.append(prev_id)
        prev_id, prev_length, prev_bike_time = (path.path_id, path.length, path.bike_time_cost)
    
    if drop_path_ids:
        self.paths = [p for p in self.paths if p.path_id not in drop_path_ids]
```

**Logic:** If path A is shorter but takes longer than path B, drop path A

---

### 7.4 Path Reclassification

**Location:** `src/gp_server/app/path_set.py`

**Purpose:** Reclassify path types after sorting/filtering.

**Algorithm:**
```python
def reclassify_path_types(self):
    """Reclassifies first path as fastest, rest as exposure optimized."""
    exp_path_type = path_type_by_routing_mode[self.routing_mode]
    for idx, path in enumerate(self.paths):
        if idx == 0:
            path.set_path_type(PathType.FASTEST)
            path.set_path_id(PathType.FASTEST.value)
        elif path.path_type == PathType.FASTEST:
            path.set_path_type(exp_path_type)
            path.set_path_id('f2')
```

---

## 8. Graph I/O Algorithms

### 8.1 GraphML I/O with Attribute Conversion

**Location:** `src/common/igraph.py`

**Purpose:** Read/write GraphML files with automatic type conversion.

**Reading Algorithm:**
```python
def read_graphml(graph_file: str, log=None) -> ig.Graph:
    """Loads igraph graph from GraphML with attribute conversion."""
    G = ig.Graph()
    G = G.Read_GraphML(graph_file)
    del(G.vs['id'])
    
    # Convert node attributes
    for attr in G.vs[0].attributes():
        try:
            converter = __value_converter_by_node_attribute[Node(attr)]
            G.vs[attr] = [converter(value) for value in list(G.vs[attr])]
        except Exception:
            if log:
                log.warning(f'Failed to read node attribute {attr}')
    
    # Convert edge attributes
    for attr in G.es[0].attributes():
        try:
            converter = __value_converter_by_edge_attribute[Edge(attr)]
            G.es[attr] = [converter(value) for value in list(G.es[attr])]
        except Exception:
            if log:
                log.warning(f'Failed to read edge attribute {attr}')
    
    return G
```

**Type Converters:**
- `to_int`: String → integer
- `to_float`: String → float
- `to_bool`: String → boolean
- `to_geom`: WKT → Shapely geometry
- `to_dict`: String → dictionary

**Writing Algorithm:**
```python
def export_to_graphml(G: ig.Graph, graph_file: str, n_attrs: List[Node] = [], e_attrs: List[Edge] = []):
    """Writes graph to GraphML with selected attributes."""
    Gc = G.copy()
    
    # Convert attributes to strings
    for attr in Node:
        if attr.value in Gc.vs[0].attributes():
            Gc.vs[attr.value] = [as_string(value) for value in list(Gc.vs[attr.value])]
    
    for attr in Edge:
        if attr.value in Gc.es[0].attributes():
            Gc.es[attr.value] = [as_string(value) for value in list(Gc.es[attr.value])]
    
    Gc.save(graph_file, format='graphml')
```

---

## Summary of Algorithm Categories

| Category | Algorithms | Key Libraries |
|----------|------------|---------------|
| **Routing** | Dijkstra, Multi-criteria weighted shortest path | igraph |
| **Spatial** | CRS projection, Nearest point/line, Line splitting, Spatial indexing | pyproj, shapely, geopandas |
| **Environmental Cost** | AQI cost, Noise cost (logarithmic), GVI cost | Custom |
| **Exposure Aggregation** | AQI/noise/GVI class aggregation, Weighted means | Custom |
| **Biking Cost** | Bikeability classification, Time/safety costs | Custom |
| **AQI Processing** | NetCDF→GeoTIFF, Scale/offset correction, Nodata filling, Raster sampling | xarray, rioxarray, rasterio |
| **Path Processing** | Deduplication, Geometry overlay filtering, Sorting | Custom |
| **Graph I/O** | GraphML read/write with type conversion | igraph |

---

## Algorithm Complexity Summary

| Algorithm | Time Complexity | Space Complexity |
|-----------|-----------------|------------------|
| Dijkstra | $O((V+E)\log V)$ | $O(V)$ |
| Nearest node/edge (spatial index) | $O(\log n)$ | $O(n)$ |
| CRS projection | $O(1)$ per point | $O(1)$ |
| Line splitting | $O(n)$ | $O(n)$ |
| Exposure aggregation | $O(n)$ | $O(k)$ |
| Path deduplication | $O(n)$ | $O(1)$ |
| GraphML read/write | $O(V+E)$ | $O(V+E)$ |
| Raster sampling | $O(n)$ | $O(1)$ |
| Nodata filling | $O(w \times h)$ | $O(w \times h)$ |

---

## Key Formulas

### AQI Cost
$$
\text{Cost} = \text{BaseCost} \times (1 + \frac{\text{AQI}-1}{4} \times \text{sensitivity})
$$

### Noise Cost (Logarithmic)
$$
\text{db\_cost} = \frac{10^{0.03 \times \text{db}}}{100}
$$

### GVI Cost
$$
\text{Cost} = \text{BaseCost} \times (1 + (1-\text{GVI}) \times \text{sensitivity})
$$

### Weighted Mean
$$
\text{Mean} = \frac{\sum (\text{value}_i \times \text{weight}_i)}{\sum \text{weight}_i}
$$

---

**Document Version:** 1.0  
**Last Updated:** May 11, 2026
