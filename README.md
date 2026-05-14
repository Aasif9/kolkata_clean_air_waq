# Kolkata AQI Clean Route Backend

A pollution-aware routing system for Kolkata that helps users find cleaner routes by avoiding high Air Quality Index (AQI) areas. The system uses real-time WAQI (World Air Quality Index) data to provide accurate pollution-aware route planning.

## Features

- **100+ Real AQI Stations** across 20km x 20km Kolkata region (via WAQI Map Bounds API)
- **Real-time AQI Data** from WAQI (World Air Quality Index)
- **Dual Routing**: Fastest vs Cleanest path comparison
- **AQI Interpolation** (IDW) for pollution estimation between stations
- **REST API** for integration with frontend applications
- **Dijkstra's Algorithm** with pollution-weighted edge weights
- **Automatic Fallback** to dummy data if API fails

## Setup

### Prerequisites
- Python 3.7+
- pip

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Download Kolkata road network (first time only):
```bash
python basic_network.py
```

3. Set up WAQI API token:
```bash
# Option A: Environment variable
export WAQI_TOKEN="your_token_here"

# Option B: Token file
echo "your_token_here" > waqi_token.txt
```

4. Start API server with real data:
```bash
export DATA_SOURCE=real
python dummy_api.py
```

5. Start frontend:
```bash
cd frontend
python3 -m http.server 8000
```

### Using Dummy Data (Fallback)

If you don't have a WAQI token or want to use dummy data:

```bash
export DATA_SOURCE=dummy
python dummy_aqi_generator.py
python dummy_api.py
```

## API Endpoints

- `GET /` - System status (shows data source: dummy or real)
- `GET /stations` - Get all AQI stations (includes data_source field)
- `GET /routes/clean?start_lat=X&start_lon=Y&end_lat=A&end_lon=B&pollution_factor=2.0` - Get clean vs fast routes
- `GET /test` - Test with sample coordinates

## Data Sources

### Real WAQI Data (Recommended)
- **API**: WAQI Map Bounds API
- **Coverage**: 100+ stations across Kolkata metropolitan area
- **Includes**: Official CAAQMS stations + community sensors (GAIA, PurpleAir)
- **Bounding Box**: 22.390,88.150,22.750,88.550 (20km radius)
- **Update Frequency**: Real-time (cached to minimize API calls)

### Dummy Data (Fallback)
- **Stations**: 25 simulated stations
- **Coverage**: 15km x 15km region
- **Pollution Patterns**: Realistic Kolkata pollution hotspots

## Algorithm

### Routing Algorithm
- **Fastest Route**: Dijkstra's algorithm with travel time as edge weight
- **Cleanest Route**: Dijkstra's algorithm with pollution-weighted edges
- **Weight Formula**: `travel_time × (1 + pollution_factor × (AQI / 100))`
- **AQI Interpolation**: Inverse Distance Weighting (IDW) between stations

### Route Comparison
- Clean route with pollution avoidance
- Fast route with shortest distance
- AQI improvement metrics
- Distance/time trade-offs
- Pollution exposure calculation

## Project Structure

```
clean-air-dummy-data/
├── dummy_api.py              # Flask API server (supports dummy & real data)
├── real_aqi_fetcher.py       # WAQI Map Bounds API fetcher
├── simple_router.py          # Routing algorithm (Dijkstra with pollution weights)
├── dummy_aqi_generator.py    # Generates dummy AQI stations
├── dummy_aqi_interpolator.py # AQI interpolation (IDW)
├── basic_network.py          # Downloads/loads road network
├── kolkata_road_network.pkl  # Cached road network (16MB)
├── kolkata_dummy_stations.json # Cached dummy stations
├── kolkata_real_stations.json # Cached real WAQI stations
├── waqi_token.txt            # WAQI API token
├── WAQI_SETUP_GUIDE.md      # Detailed setup guide for real WAQI data
├── requirements.txt          # Python dependencies
├── frontend/                 # Frontend files
│   ├── index.html           # Main UI
│   ├── css/                 # Stylesheets
│   └── js/                  # JavaScript
└── project_working_report.md # Comprehensive project documentation
```

## Documentation

- **WAQI_SETUP_GUIDE.md** - Detailed instructions for setting up real WAQI data
- **project_working_report.md** - Comprehensive project documentation including algorithm details

## License

This project is for educational and research purposes. WAQI API data is subject to their terms of service.
