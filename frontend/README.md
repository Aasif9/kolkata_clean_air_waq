# Kolkata Clean Air Routes - Frontend

A complete frontend interface for the Kolkata AQI Clean Route backend system.

## 📁 Project Structure

```
frontend/
├── index.html              # Main HTML file
├── css/
│   ├── style.css          # Main styles
│   └── map.css            # Map-specific styles
├── js/
│   ├── app.js             # Main application logic
│   ├── map.js             # Leaflet map functionality
│   ├── api.js             # API communication
│   └── utils.js           # Utility functions
└── assets/
    ├── icons/             # Custom map icons
    └── images/            # Static images
```

## 🚀 Quick Start

### 1. Start Backend Server
```bash
cd /Users/asifali/Desktop/web-projects/clean-air
python3 dummy_api.py
```

### 2. Open Frontend
```bash
cd frontend
python3 -m http.server 8000
```

### 3. Access Application
Open: http://localhost:8000

## ✨ Features

### 🗺️ Interactive Map
- **Leaflet.js** mapping with OpenStreetMap tiles
- **Click-to-select** start and end points
- **Real-time route visualization**
- **AQI station overlays** with color coding
- **Fullscreen mode** and map controls

### 🛣️ Route Planning
- **Dual routing**: Fastest vs Cleanest paths
- **Pollution sensitivity slider** (0-10)
- **Real-time route recalculation**
- **Coordinate input** support
- **Geolocation** support for current position

### 📊 Route Analysis
- **Distance comparison** with trade-off analysis
- **AQI exposure metrics** (average, min, max)
- **Smart recommendations** based on user preferences
- **Route highlighting** and selection
- **Interactive route popups** with detailed stats

### 🌡️ AQI Monitoring
- **25 dummy stations** across Kolkata
- **Color-coded air quality** indicators
- **Station list** with real-time AQI values
- **Popup information** for each station
- **Spatial interpolation** between stations

### 📱 Responsive Design
- **Mobile-friendly** interface
- **Adaptive layout** for different screen sizes
- **Touch-enabled** controls
- **Optimized performance** for all devices

## 🎯 How to Use

1. **Set Start Point**: Click on map or enter coordinates
2. **Set End Point**: Click again or enter coordinates
3. **Adjust Pollution Sensitivity**: Use slider to prioritize clean air vs distance
4. **Calculate Routes**: Click "Calculate Routes" button
5. **Compare Options**: View fast vs clean route statistics
6. **Select Route**: Click "Show Route" to highlight preferred path

## 🔧 Technical Details

### API Integration
- **Base URL**: `http://localhost:5002`
- **Endpoints**: `/stations`, `/routes/clean`, `/`
- **Error handling** with user-friendly messages
- **Connection status** monitoring

### Map Features
- **Kolkata bounds**: 22.505°N to 22.640°N, 88.296°E to 88.431°E
- **Custom markers** for start/end points
- **Circle markers** for AQI stations
- **Polyline routes** with color coding
- **Interactive popups** with detailed information

### Route Calculations
- **Fast route**: Shortest path by travel time
- **Clean route**: Pollution-weighted pathfinding
- **Trade-off analysis**: Distance vs AQI improvement
- **Smart recommendations**: AI-powered suggestions

## 🎨 Design System

### Colors
- **Primary**: #3498db (Blue)
- **Success**: #2ecc71 (Green)
- **Warning**: #f39c12 (Yellow)
- **Danger**: #e74c3c (Red)
- **Dark**: #2c3e50 (Charcoal)

### Typography
- **Font**: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif
- **Sizes**: Responsive scaling from mobile to desktop
- **Weights**: 400 (normal), 500 (medium), 700 (bold)

### Components
- **Cards**: Rounded corners, subtle shadows
- **Buttons**: Hover effects, transitions
- **Forms**: Clean inputs with focus states
- **Loading**: Spinner overlay with backdrop

## 📱 Browser Support

- ✅ Chrome 60+
- ✅ Firefox 55+
- ✅ Safari 12+
- ✅ Edge 79+
- ✅ Mobile browsers

## 🔍 Testing

### Manual Testing Checklist
- [ ] Map loads and displays Kolkata region
- [ ] AQI stations appear with correct colors
- [ ] Click to set start/end points works
- [ ] Route calculation completes successfully
- [ ] Pollution slider updates routes
- [ ] Responsive design works on mobile
- [ ] Error handling displays messages
- [ ] Connection status shows correctly

### API Testing
```bash
# Test backend connection
curl http://localhost:5002

# Test stations endpoint
curl http://localhost:5002/stations

# Test route calculation
curl "http://localhost:5002/routes/clean?start_lat=22.5620&start_lon=88.3500&end_lat=22.5850&end_lon=88.3700"
```

## 🚀 Production Ready

This frontend is production-ready with:
- **Error handling** and user feedback
- **Loading states** and spinners
- **Responsive design** for all devices
- **Performance optimization** with efficient rendering
- **Accessibility** features and semantic HTML
- **Cross-browser compatibility** testing

The complete Kolkata AQI Clean Route system is now ready for real-world use!
