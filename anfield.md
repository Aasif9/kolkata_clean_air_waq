# Green Paths API Architecture Analysis

## 1. Core Purpose of the API

The API is designed for:

- **Environment-aware routing**
- **Finding:**
  - Cleaner air routes
  - Quieter routes
  - Greener routes
  - Safer bike routes
- **Comparing optimized routes with fastest/shortest routes**

The word "clean" refers to:

- Fresh air paths
- Low pollution exposure routes

## 2. Main API Endpoint Structure

**Base URL:** `www.greenpaths.fi/`

**Route API Format:**
```
www.greenpaths.fi/paths/{travel_mode}/{routing_mode}/{orig_coords}/{dest_coords}
```

**Example:**
```
www.greenpaths.fi/paths/walk/green/60.20772,24.96716/60.2037,24.9653
```

## 3. Supported Travel Modes

| Mode | Description |
|------|-------------|
| walk | Walking routes |
| bike | Bicycle routes |

## 4. Supported Routing Modes

| Routing Mode | Meaning |
|--------------|---------|
| green | Greenest route |
| quiet | Least noisy route |
| clean | Lowest air pollution route |
| fast | Fastest route |
| short | Shortest route |
| safe | Safest bike route |

## 5. Main Routing Logic

### Walking Routing

The system computes:

- Shortest/Fastest route
- Exposure-optimized routes:
  - Green
  - Quiet
  - Clean

### Bicycle Routing

The system computes:

- Fastest route
- Safest route
- Exposure optimized routes:
  - Green
  - Quiet
  - Clean

## 6. Multi-Route Optimization Concept

The API does NOT return only one route.

It returns:

- Multiple candidate routes
- Different optimization strategies

This means the backend likely uses:

- Multi-objective pathfinding
- Weighted graph routing
- Cost-based route optimization

## 7. Key Optimization Parameters

The system optimizes using:

| Factor | Meaning |
|--------|---------|
| AQI | Air quality |
| Noise | Noise pollution |
| GVI | Green View Index |
| Safety | Bike safety |
| Distance | Route length |
| Travel time | Speed/cost |

## 8. Core Pathfinding Insight

The important field is: `cost_coeff`

This strongly suggests the system uses:

**Weighted Cost Functions**

Example conceptual formula:

```
TotalCost = Distance + (λ₁ × AQI) + (λ₂ × Noise) - (λ₃ × Greenery)
```

Where:

- `cost_coeff` controls environmental sensitivity
- Higher coefficient = stronger preference for cleaner/greener routes

This is a major architectural insight.

## 9. Important Route Metrics Returned

Each route contains:

| Property | Purpose |
|----------|---------|
| length | Route distance |
| aqc | Air pollution exposure |
| aqi_m | Mean AQI |
| mdB | Mean noise level |
| gvi_m | Mean greenery score |
| nei | Noise exposure index |
| len_diff | Extra distance compared to fastest route |

## 10. AQI Exposure Modeling

The API calculates:

**AQI Class Exposure**

Example:

```json
aqi_cl_exps: {
  2: 492.94
}
```

Meaning:

492.94 meters of the route passed through AQI Class 2 zones.

**AQI Classes Formula**

The README reveals this exact logic:

```
AQI Class = ⌊AQI × 2⌋ - 1
```

This converts AQI values into exposure classes.

## 11. Environmental Segment Aggregation

The API splits routes into:

- Edge segments
- Environmental exposure segments

Each edge contains:

- AQI class
- Noise level
- Greenery class

This means:

- The road graph stores environmental metadata per edge.

## 12. GeoJSON-Based Architecture

The API returns:

- **Path_FC** - Complete routes
- **Edge_FC** - Individual route segments

Both use:

- GeoJSON FeatureCollections

This is important because:

- Frontend maps can render them directly
- GIS libraries can process them easily

## 13. Evidence of Graph-Based Routing

The README confirms:

- `edge_ids`
- `edge_data`

This strongly indicates:

- Road network graph structure
- Node-edge graph database
- Graph traversal algorithms

Likely algorithms:

- Dijkstra
- A*
- Multi-criteria shortest path

## 14. Dynamic Environmental Weighting

The API generates multiple versions of routes:

Example:

```json
"id": "q_20",
"cost_coeff": 20
```

Meaning:

- The algorithm runs multiple times
- Each run uses different environmental penalties

This is a very important architectural discovery.

## 15. Environmental Cost Computation

The system calculates:

- Air Pollution Cost (`aqc`)
- Noise Exposure Index (`nei`)
- Distance-Normalized Metrics (`aqc_norm`, `nei_norm`)

This means:

- Exposure is integrated across route distance.

Likely formula:

```
Exposure Cost = Σ (EdgeLengthᵢ × PollutionWeightᵢ)
```

## 16. Edge-Based Environmental Modeling

The route graph likely contains per-edge metadata:

**Edge Attribute:**
- AQI
- Noise
- Greenery
- Safety
- Length
- Travel time

This is the key to reproducing the system.

## 17. Missing Data Handling

The API explicitly tracks:

| Property | Purpose |
|----------|---------|
| missing_aqi | Tracks missing AQI data |
| missing_gvi | Tracks missing greenery data |
| missing_noises | Tracks missing noise data |

Meaning:

- The backend supports incomplete environmental datasets
- It likely uses:
  - Interpolation
  - Fallback values
  - Nearest-neighbor estimation

## 18. Research Mode Insights

Research mode reveals critical implementation details:

**Additional Edge Data (`edge_data`)**

Contains:

- length
- AQI
- GVI
- noise
- coordinates

This confirms:

- Environmental data is attached directly to graph edges.

## 19. Most Important Architectural Discovery

The system is fundamentally:

**A Multi-Criteria Graph Routing Engine**

It combines:

| Component | Role |
|-----------|------|
| Road Graph | Navigation |
| AQI Layer | Pollution optimization |
| Noise Layer | Quiet routing |
| Greenery Layer | Scenic routing |
| Cost Function | Route scoring |
| Pathfinding Algorithm | Route generation |

## 20. Likely Internal Routing Pipeline

The backend likely works like this:

```
User Origin/Destination
        ↓
Nearest Graph Nodes
        ↓
Load Road Network Graph
        ↓
Attach Environmental Weights
        ↓
Run Weighted Pathfinding
        ↓
Generate Multiple Candidate Routes
        ↓
Compute Exposure Metrics
        ↓
Return GeoJSON
```

## 21. Key Algorithms Likely Used

Based on the README:

| Algorithm | Likelihood |
|-----------|------------|
| Dijkstra | Very High |
| A* | Very High |
| Multi-objective optimization | High |
| Pareto routing | Possible |
| Weighted shortest path | Confirmed |
| Spatial nearest-neighbor search | Confirmed |

## 22. Database & GIS Stack Likely Used

The architecture strongly suggests:

| Technology | Purpose |
|------------|---------|
| PostGIS | Spatial graph storage |
| GeoJSON | API responses |
| NetworkX / pgRouting | Pathfinding |
| R-Tree / KD-Tree | Spatial search |
| OpenStreetMap | Road graph |

## 23. How You Can Rebuild This for Kolkata

You would need:

**AQI Sources:**
- CPCB stations
- OpenAQ
- WAQI
- Kolkata pollution monitoring stations

**Road Network:**
- OpenStreetMap Kolkata road graph

**Graph Construction**

Each road edge should contain:

```json
{
  "length": 120,
  "aqi": 2.8,
  "noise": 65,
  "gvi": 0.4,
  "bike_safety": 0.8
}
```

**Routing Formula**

You can recreate the logic using:

```
RouteCost = Distance + α(AQI) + β(Noise) - γ(Greenery)
```

Where:

- α = pollution sensitivity
- β = noise sensitivity
- γ = greenery preference

## 24. Most Critical Engineering Insight

This API is NOT simply:

> Google Maps + AQI overlay

It is:

> A fully custom weighted environmental routing engine.

The environmental data is deeply integrated into:

- Graph edges
- Cost functions
- Pathfinding algorithms
- Exposure scoring systems
- GeoJSON route generation
