// Map Module
class AQIMap {
    constructor(containerId = 'map') {
        this.container = containerId;
        this.map = null;
        this.markers = {
            start: null,
            end: null,
            stations: [],
            routes: {
                clean: null,
                fast: null
            }
        };
        
        // Kolkata bounds
        this.kolkataBounds = [
            [22.505, 88.296],  // Southwest
            [22.640, 88.431]   // Northeast
        ];
        
        this.init();
    }
 
    init() {
        // Initialize Leaflet map
        this.map = L.map(this.container).fitBounds(this.kolkataBounds);
        
        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(this.map);
        
        // Add click handler
        this.map.on('click', (e) => this.handleMapClick(e));
        
        console.log('Map initialized');
    }
 
    handleMapClick(event) {
        const { lat, lng } = event.latlng;
        
        // Emit custom event for app to handle
        const mapClickEvent = new CustomEvent('mapClick', {
            detail: { lat, lng }
        });
        document.dispatchEvent(mapClickEvent);
    }
 
    addStartMarker(lat, lon) {
        if (this.markers.start) {
            this.map.removeLayer(this.markers.start);
        }
        
        this.markers.start = L.marker([lat, lon], {
            icon: L.divIcon({
                className: 'custom-marker start-marker',
                html: '<i class="fas fa-play"></i>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            })
        }).addTo(this.map);
        
        this.markers.start.bindPopup('Start Point').openPopup();
    }
 
    addEndMarker(lat, lon) {
        if (this.markers.end) {
            this.map.removeLayer(this.markers.end);
        }
        
        this.markers.end = L.marker([lat, lon], {
            icon: L.divIcon({
                className: 'custom-marker end-marker',
                html: '<i class="fas fa-flag-checkered"></i>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            })
        }).addTo(this.map);
        
        this.markers.end.bindPopup('End Point').openPopup();
    }
 
    addAQIStations(stations) {
        // Clear existing station markers
        this.clearStationMarkers();
        
        stations.forEach(station => {
            const color = Utils.getAQIColor(station.aqi);
            const category = Utils.getAQICategory(station.aqi);
            
            const marker = L.circleMarker([station.lat, station.lon], {
                radius: 8,
                fillColor: color,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8,
                className: `aqi-station ${category}` 
            }).addTo(this.map);
            
            marker.bindPopup(`
                <div class="station-popup">
                    <h4>${station.name}</h4>
                    <p><strong>AQI:</strong> ${station.aqi}</p>
                    <p><strong>Category:</strong> ${Utils.getAQIDescription(station.aqi)}</p>
                    <p><strong>Location:</strong> ${Utils.formatCoordinates(station.lat, station.lon)}</p>
                </div>
            `);
            
            this.markers.stations.push(marker);
        });
    }
 
    drawRoute(routeData, type) {
        // Clear existing route of this type
        if (this.markers.routes[type]) {
            this.map.removeLayer(this.markers.routes[type]);
        }
        
        // Handle different coordinate formats
        let coordinates;
        if (routeData.waypoints) {
            // Clean route has waypoints with lat, lon, aqi
            coordinates = routeData.waypoints.map(wp => [wp.lat, wp.lon]);
        } else if (routeData.coordinates) {
            // Fast route has coordinates as array of arrays
            coordinates = routeData.coordinates;
        } else {
            console.error('Invalid route data format:', routeData);
            return;
        }
        
        const color = type === 'clean' ? '#2ecc71' : '#e74c3c';
        const weight = type === 'clean' ? 5 : 4;
        
        const polyline = L.polyline(coordinates, {
            color: color,
            weight: weight,
            opacity: 0.8,
            smoothFactor: 1
        }).addTo(this.map);
        
        // Add popup with route information if analysis is available
        if (routeData.analysis) {
            const analysis = routeData.analysis;
            polyline.bindPopup(`
                <div class="route-popup">
                    <h4>${type === 'clean' ? 'Clean Route' : 'Fast Route'}</h4>
                    <p><strong>Distance:</strong> ${Utils.formatDistance(analysis.total_distance_km)}</p>
                    <p><strong>Avg AQI:</strong> ${analysis.average_aqi.toFixed(1)}</p>
                    <p><strong>Max AQI:</strong> ${analysis.max_aqi.toFixed(1)}</p>
                    <p><strong>Min AQI:</strong> ${analysis.min_aqi.toFixed(1)}</p>
                </div>
            `);
        }
        
        this.markers.routes[type] = polyline;
        
        // Fit map to show both routes
        this.fitRoutes();
    }
 
    fitRoutes() {
        const bounds = L.latLngBounds();
        
        // Add start and end markers
        if (this.markers.start) bounds.extend(this.markers.start.getLatLng());
        if (this.markers.end) bounds.extend(this.markers.end.getLatLng());
        
        // Add route bounds
        Object.values(this.markers.routes).forEach(route => {
            if (route) bounds.extend(route.getBounds());
        });
        
        if (bounds.isValid()) {
            this.map.fitBounds(bounds, { padding: [50, 50] });
        }
    }
 
    highlightRoute(type) {
        // Reset all routes
        Object.keys(this.markers.routes).forEach(routeType => {
            const route = this.markers.routes[routeType];
            if (route) {
                const baseWeight = routeType === 'clean' ? 5 : 4;
                const baseOpacity = routeType === 'clean' ? 0.8 : 0.8;
                
                route.setStyle({
                    weight: baseWeight,
                    opacity: baseOpacity
                });
            }
        });
        
        // Highlight selected route
        const selectedRoute = this.markers.routes[type];
        if (selectedRoute) {
            selectedRoute.setStyle({
                weight: 7,
                opacity: 1.0
            });
        }
    }
 
    clearRoutes() {
        Object.values(this.markers.routes).forEach(route => {
            if (route) this.map.removeLayer(route);
        });
        this.markers.routes = { clean: null, fast: null };
    }
 
    clearStationMarkers() {
        this.markers.stations.forEach(marker => {
            this.map.removeLayer(marker);
        });
        this.markers.stations = [];
    }
 
    clearMarkers() {
        if (this.markers.start) {
            this.map.removeLayer(this.markers.start);
            this.markers.start = null;
        }
        
        if (this.markers.end) {
            this.map.removeLayer(this.markers.end);
            this.markers.end = null;
        }
        
        this.clearRoutes();
    }
 
    centerMap() {
        this.map.fitBounds(this.kolkataBounds);
    }
 
    toggleFullscreen() {
        const mapContainer = document.getElementById('map');
        
        if (!document.fullscreenElement) {
            mapContainer.requestFullscreen().catch(err => {
                console.error('Error attempting to enable fullscreen:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }
}
 
// Export for use in other modules
window.AQIMap = AQIMap;
