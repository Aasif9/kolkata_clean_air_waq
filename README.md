# Kolkata AQI Clean Route Backend

A backend system for finding pollution-aware routes in Kolkata using dummy AQI data.

## Features

- **25 Dummy AQI Stations** across 15km x 15km Kolkata region
- **Realistic Pollution Patterns** with industrial hotspots and clean areas
- **Dual Routing**: Fastest vs Cleanest path comparison
- **AQI Interpolation** for pollution estimation between stations
- **REST API** for integration with frontend applications

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Generate dummy AQI stations:
```bash
python dummy_aqi_generator.py
```

3. Download Kolkata road network:
```bash
python basic_network.py
```

4. Start API server:
```bash
python dummy_api.py
```

5. Test the system:
```bash
python test_complete_system.py
```

## API Endpoints

- `GET /` - System status
- `GET /stations` - Get all AQI stations
- `GET /routes/clean?start_lat=X&start_lon=Y&end_lat=A&end_lon=B` - Get clean vs fast routes
- `GET /test` - Test with sample coordinates

## Pollution Sources

The dummy system includes realistic pollution patterns:
- **Howrah Industrial**: High AQI (150-180)
- **Salt Lake Traffic**: Moderate-high AQI (120-160)
- **Dumdum Airport**: High AQI (140-170)
- **Victoria Memorial**: Low AQI (60-70)
- **Maidan**: Low AQI (65-75)

## Route Comparison

The system provides:
- Clean route with pollution avoidance
- Fast route with shortest distance
- AQI improvement metrics
- Distance/time trade-offs

## Next Steps

Replace dummy data with real CPCB/WAQI API data when available.
