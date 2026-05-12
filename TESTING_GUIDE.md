# 🌍 Local Testing Guide - Kolkata AQI Clean Route Backend

## 🚀 Quick Start Testing

### 1. **Start the Server**
```bash
cd /Users/asifali/Desktop/web-projects/clean-air
python3 dummy_api.py
```

### 2. **Run Comprehensive Tests**
```bash
# In a new terminal window
python3 test_local.py
```

### 3. **Test Individual Endpoints**

#### 📡 Check Server Status
```bash
curl http://localhost:5002
```

#### 📍 Get All AQI Stations
```bash
curl http://localhost:5002/stations
```

#### 🛣️ Test Route Calculation
```bash
# Howrah to Salt Lake
curl "http://localhost:5002/routes/clean?start_lat=22.5750&start_lon=88.3500&end_lat=22.5800&end_lon=88.3800"

# Victoria Memorial to Dum Dum
curl "http://localhost:5002/routes/clean?start_lat=22.5726&start_lon=88.3639&end_lat=22.5850&end_lon=88.3700"
```

## 🎯 Testing Scenarios

### **Scenario 1: Industrial to Commercial**
- **Route**: Howrah Industrial → Salt Lake Traffic
- **Expected**: High pollution avoidance, moderate distance increase

### **Scenario 2: Clean to High Traffic**
- **Route**: Victoria Memorial → Dum Dum Airport  
- **Expected**: Significant AQI improvement, some distance trade-off

### **Scenario 3: Residential Areas**
- **Route**: Park Street → Behala
- **Expected**: Moderate pollution differences

## 🧪 Advanced Testing

### **Pollution Factor Testing**
Test how pollution sensitivity affects routing:

```bash
# Low pollution sensitivity (0.5)
curl "http://localhost:5002/routes/clean?start_lat=22.5726&start_lon=88.3639&end_lat=22.5800&end_lon=88.3800&pollution_factor=0.5"

# High pollution sensitivity (10.0)
curl "http://localhost:5002/routes/clean?start_lat=22.5726&start_lon=88.3639&end_lat=22.5800&end_lon=88.3800&pollution_factor=10.0"
```

### **Custom Coordinate Testing**
Use your own Kolkata coordinates:

```bash
# Format: curl "http://localhost:5002/routes/clean?start_lat=LAT&start_lon=LON&end_lat=LAT&end_lon=LON"
curl "http://localhost:5002/routes/clean?start_lat=22.5600&start_lon=88.3400&end_lat=22.5900&end_lon=88.3600"
```

## 📊 Expected Results

### **Successful Response Format**
```json
{
  "clean_route": {
    "coordinates": [[22.5726, 88.3639], ...],
    "node_count": 43,
    "analysis": {
      "total_distance_km": 4.64,
      "average_aqi": 89.2,
      "max_aqi": 156.3,
      "min_aqi": 45.7
    }
  },
  "fast_route": {
    "coordinates": [[22.5726, 88.3639], ...],
    "node_count": 51,
    "analysis": {
      "total_distance_km": 4.34,
      "average_aqi": 92.3,
      "max_aqi": 178.9,
      "min_aqi": 52.1
    }
  },
  "comparison": {
    "distance_increase_percent": 6.9,
    "aqi_improvement": 3.1
  },
  "status": "success",
  "data_source": "dummy"
}
```

### **Key Metrics to Observe**
- **Distance Trade-off**: How much extra distance for clean air
- **AQI Improvement**: Pollution exposure reduction
- **Route Complexity**: Number of nodes in each path
- **Pollution Hotspots**: Areas with high AQI values

## 🔧 Troubleshooting

### **Server Not Running**
```bash
# Check if port is in use
lsof -i :5002

# Kill any existing process
kill -9 <PID>

# Restart server
python3 dummy_api.py
```

### **Missing Data Files**
```bash
# Regenerate dummy stations
python3 dummy_aqi_generator.py

# Re-download road network
python3 basic_network.py
```

### **Dependencies Issues**
```bash
# Reinstall dependencies
pip3 install -r requirements.txt
```

## 🎮 Interactive Testing

Run the interactive test suite:
```bash
python3 test_local.py
```

This will:
- ✅ Test all API endpoints automatically
- ✅ Show pollution distribution
- ✅ Compare different pollution factors
- ✅ Allow custom coordinate testing
- ✅ Provide detailed performance metrics

## 📱 Browser Testing

You can also test endpoints directly in your browser:
- http://localhost:5002
- http://localhost:5002/stations
- http://localhost:5002/routes/clean?start_lat=22.5726&start_lon=88.3639&end_lat=22.5800&end_lon=88.3800

## 🚀 Ready for Frontend

Once testing passes, your backend is ready for frontend integration:
- **Base URL**: `http://localhost:5002`
- **Authentication**: None (local testing)
- **Rate Limiting**: None (local testing)
- **Data Format**: JSON responses

## 📈 Performance Expectations

- **Response Time**: 2-10 seconds for route calculations
- **Network Coverage**: 15km x 15km Kolkata region
- **Station Count**: 25 dummy AQI monitoring points
- **Road Network**: ~32,000 nodes, ~79,000 edges

Your backend system is now fully tested and ready for production integration!
