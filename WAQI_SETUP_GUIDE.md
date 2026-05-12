# WAQI Real API Setup Guide

This guide explains how to set up the Kolkata AQI Routing System to use real-time WAQI (World Air Quality Index) data instead of dummy data.

## Why Use Real WAQI Data?

The current dummy system uses only 25 simulated AQI stations. The real WAQI Map Bounds API can retrieve **ALL** stations in Kolkata, including:
- Official government stations (CAAQMS)
- Private/community sensor networks (GAIA, PurpleAir)
- University monitoring stations
- Additional community sensors

This can give you 30+ stations instead of just 8 or 25, providing much better AQI coverage for route planning.

## Step 1: Confirm Your Email and Get Token

1. Click the confirmation link from WAQI:
   ```
   https://aqicn.org/data-platform/token-confirm/ef18ef73-d35b-4d6a-a492-0bbea7429548
   ```

2. This will confirm your email (asifalidev9@gmail.com) and show you your API token

3. Copy your API token (it will look something like: `abcdef123456`)

## Step 2: Set Up Your Token

You have two options to set your WAQI token:

### Option A: Environment Variable (Recommended)
```bash
export WAQI_TOKEN="your_actual_token_here"
```

### Option B: Token File
Create a file named `waqi_token.txt` in the project directory:
```bash
echo "your_actual_token_here" > waqi_token.txt
```

## Step 3: Set Data Source to Real

```bash
export DATA_SOURCE=real
```

## Step 4: Restart the Backend Server

Stop the current backend server (Ctrl+C) and restart it:

```bash
python dummy_api.py
```

The server will now:
1. Fetch real AQI stations from WAQI Map Bounds API
2. Use the bounding box: 22.390,88.150,22.750,88.550 (covers 20km radius around Kolkata)
3. Cache the stations in `kolkata_real_stations.json`
4. Use real-time AQI data for routing

## Step 5: Verify Real Data is Working

Check the API response:
```bash
curl http://localhost:5002/stations
```

You should see:
- `data_source: "real"` in the response
- More stations than the dummy 25 (typically 30+)
- Real station names from WAQI

## API Endpoint Details

The system uses the WAQI Map Bounds API:
```
https://api.waqi.info/v2/map/bounds/?latlng={minLat,minLng,maxLat,maxLng}&token={YOUR_TOKEN}
```

**Bounding Box for Kolkata (20km radius):**
- South: 22.390°N
- West: 88.150°E
- North: 22.750°N
- East: 88.550°E

This covers the entire Kolkata metropolitan area including:
- Howrah
- Salt Lake
- Dum Dum
- Behala
- Tollygunge
- And surrounding areas

## Switching Back to Dummy Data

If you need to switch back to dummy data:
```bash
export DATA_SOURCE=dummy
python dummy_api.py
```

## Troubleshooting

### Error: "WAQI token required"
- Make sure you've set the WAQI_TOKEN environment variable or created waqi_token.txt
- Verify your token is correct (no extra spaces or characters)

### Error: "Failed to fetch real stations"
- Check your internet connection
- Verify your WAQI token is valid
- The system will automatically fall back to dummy data if real data fails

### Only getting 8 stations
- Make sure you're using the Map Bounds API (not City Feed API)
- The system uses Map Bounds API by default when DATA_SOURCE=real
- Check the bounding box coordinates in real_aqi_fetcher.py

## Testing Real Data Fetch

You can test the WAQI fetcher independently:
```bash
python real_aqi_fetcher.py
```

This will:
1. Fetch stations from WAQI
2. Display statistics
3. Save to kolkata_real_stations.json
4. Show sample stations

## Benefits of Real Data

1. **More Stations**: 30+ stations vs 25 dummy stations
2. **Real-time**: Actual current AQI values
3. **Better Coverage**: Includes community sensors, not just official stations
4. **Accurate Routing**: More accurate pollution-aware route planning
5. **No Simulation**: Real pollution patterns, not estimated

## Rate Limits

WAQI free tier has rate limits:
- 1,000 requests per day
- 1 request per second

The system caches stations in `kolkata_real_stations.json` to minimize API calls. You can refresh the data by deleting the cache file and restarting the server.

## Next Steps

After setting up real data:
1. Test route calculations with real AQI values
2. Compare results with dummy data
3. Adjust pollution_factor parameter for optimal routing
4. Monitor AQI changes throughout the day
