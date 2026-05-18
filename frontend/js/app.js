// Main Application Controller
class AQIRouteApp {
    constructor() {
        this.api = new AQIAPI();
        this.map = new AQIMap();
        this.storage = new RouteStorage();
        this.currentRoutes = null;
        this.selectedRoute = null;
        this.startPoint = null;
        this.endPoint = null;
        
        this.init();
    }
 
    async init() {
        console.log('Initializing Kolkata AQI Route App...');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Check backend connection
        await this.checkBackendConnection();
        
        // Load AQI stations
        await this.loadAQIStations();
        
        // Load saved routes
        this.loadSavedRoutes();
        
        // Update pollution slider
        this.updatePollutionDescription();
        
        console.log('App initialized successfully');
    }
 
    setupEventListeners() {
        // Map click events
        document.addEventListener('mapClick', (e) => this.handleMapClick(e));
        
        // Control buttons
        document.getElementById('calculateBtn').addEventListener('click', () => this.calculateRoutes());
        document.getElementById('clearBtn').addEventListener('click', () => this.clearAll());
        document.getElementById('centerBtn').addEventListener('click', () => this.map.centerMap());
        document.getElementById('fullscreenBtn').addEventListener('click', () => this.map.toggleFullscreen());
        document.getElementById('viewEndpointsBtn').addEventListener('click', () => this.viewRouteDetails());
        
        
        // Pollution slider
        const slider = document.getElementById('pollutionSlider');
        slider.addEventListener('input', () => this.updatePollutionDescription());
        slider.addEventListener('change', () => this.recalculateIfRoutesExist());
        
        // Input fields
        document.getElementById('startInput').addEventListener('change', () => this.updatePointFromInput('start'));
        document.getElementById('endInput').addEventListener('change', () => this.updatePointFromInput('end'));
        
        // Location buttons
        document.getElementById('locateStartBtn').addEventListener('click', () => this.locatePoint('start'));
        document.getElementById('locateEndBtn').addEventListener('click', () => this.locatePoint('end'));
        
        // Storage controls
        document.getElementById('refreshSavedBtn').addEventListener('click', () => this.loadSavedRoutes());
        document.getElementById('exportRoutesBtn').addEventListener('click', () => this.exportRoutes());
        document.getElementById('importRoutesBtn').addEventListener('click', () => this.importRoutes());
        document.getElementById('importFileInput').addEventListener('change', (e) => this.handleImportFile(e));
        
        // Error toast close
        document.getElementById('closeErrorBtn').addEventListener('click', () => {
            document.getElementById('errorToast').classList.remove('active');
        });
    }
 
    async checkBackendConnection() {
        const statusElement = document.getElementById('backendStatus');
        statusElement.textContent = 'Checking...';
        statusElement.className = 'status-value';
        
        try {
            const result = await this.api.testConnection();
            
            if (result.success) {
                statusElement.textContent = `Online (${result.responseTime}ms)`;
                statusElement.className = 'status-value online';
            } else {
                statusElement.textContent = 'Offline';
                statusElement.className = 'status-value offline';
                Utils.showError('Backend server is offline. Please start the server.');
            }
        } catch (error) {
            statusElement.textContent = 'Error';
            statusElement.className = 'status-value offline';
            Utils.showError('Failed to connect to backend server.');
        }
    }
 
    async loadAQIStations() {
        try {
            const data = await this.api.getStations();
            
            // Update map
            this.map.addAQIStations(data.stations);
            
            // Update stations list
            this.updateStationsList(data.stations);
            
            // Update status
            document.getElementById('stationCount').textContent = data.total_stations;
            
            console.log(`Loaded ${data.total_stations} AQI stations`);
        } catch (error) {
            Utils.showError(error.message);
        }
    }
 
    updateStationsList(stations) {
        const stationsList = document.getElementById('stationsList');
        
        // Sort stations by AQI (highest first)
        const sortedStations = [...stations].sort((a, b) => b.aqi - a.aqi);
        
        // Create HTML for top 10 stations
        const html = sortedStations.slice(0, 10).map(station => {
            const category = Utils.getAQICategory(station.aqi);
            return `
                <div class="station-item">
                    <span class="station-name">${station.name}</span>
                    <span class="station-aqi aqi-${category}">${station.aqi}</span>
                </div>
            `;
        }).join('');
        
        stationsList.innerHTML = html;
    }
 
    handleMapClick(event) {
        const { lat, lng } = event.detail;
        
        if (!this.startPoint) {
            this.setStartPoint(lat, lng);
        } else if (!this.endPoint) {
            this.setEndPoint(lat, lng);
        } else {
            // Reset and set new start point
            this.clearRoutes();
            this.setStartPoint(lat, lng);
            this.endPoint = null;
            document.getElementById('endInput').value = '';
        }
    }
 
    setStartPoint(lat, lon) {
        this.startPoint = { lat, lon };
        document.getElementById('startInput').value = Utils.formatCoordinates(lat, lon);
        this.map.addStartMarker(lat, lon);
    }
 
    setEndPoint(lat, lon) {
        this.endPoint = { lat, lon };
        document.getElementById('endInput').value = Utils.formatCoordinates(lat, lon);
        this.map.addEndMarker(lat, lon);
    }
 
    updatePointFromInput(type) {
        const inputId = type === 'start' ? 'startInput' : 'endInput';
        const input = document.getElementById(inputId);
        const coords = Utils.parseCoordinates(input.value);
        
        if (coords) {
            if (type === 'start') {
                this.setStartPoint(coords.lat, coords.lon);
            } else {
                this.setEndPoint(coords.lat, coords.lon);
            }
        } else {
            Utils.showError(`Invalid coordinates format. Use: lat,lon (e.g., 22.5726,88.3639)`);
        }
    }
 
    locatePoint(type) {
        // Get user's current location
        if (navigator.geolocation) {
            Utils.setLoading(true);
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const { latitude, longitude } = position.coords;
                    
                    // Check if within Kolkata bounds
                    if (this.isWithinKolkataBounds(latitude, longitude)) {
                        if (type === 'start') {
                            this.setStartPoint(latitude, longitude);
                        } else {
                            this.setEndPoint(latitude, longitude);
                        }
                    } else {
                        Utils.showError('Location is outside Kolkata service area');
                    }
                    
                    Utils.setLoading(false);
                },
                (error) => {
                    Utils.showError('Unable to get your location. Please enter coordinates manually.');
                    Utils.setLoading(false);
                }
            );
        } else {
            Utils.showError('Geolocation is not supported by your browser');
        }
    }
 
    isWithinKolkataBounds(lat, lon) {
        return lat >= 22.505 && lat <= 22.640 && lon >= 88.296 && lon <= 88.431;
    }
 
    async calculateRoutes() {
        if (!this.startPoint || !this.endPoint) {
            Utils.showError('Please select both start and end points');
            return;
        }
        
        const pollutionFactor = parseFloat(document.getElementById('pollutionSlider').value);
        
        Utils.setLoading(true);
        
        try {
            const data = await this.api.getCleanRoute(
                this.startPoint.lat,
                this.startPoint.lon,
                this.endPoint.lat,
                this.endPoint.lon,
                pollutionFactor
            );
            
            this.currentRoutes = data;
            this.displayRoutes(data);
            
        } catch (error) {
            Utils.showError(error.message);
        } finally {
            Utils.setLoading(false);
        }
    }

    displayRoutes(data) {
        // Draw routes on map
        this.map.drawRoute(data.clean_route, 'clean');
        this.map.drawRoute(data.fast_route, 'fast');
        
        // Update route summary
        this.updateRouteSummary(data.clean_route);
        
        // Update waypoints list
        this.updateWaypointsList(data.clean_route.waypoints);
        
        // Store full route data for the separate page
        this.currentRoutes = data;
        
        // Save route to localStorage
        try {
            this.storage.saveRoute(data, this.startPoint, this.endPoint);
            console.log('Route saved to localStorage');
        } catch (error) {
            console.error('Failed to save route:', error);
        }
        
        // Highlight clean route on map
        this.map.highlightRoute('clean');
    }

    updateRouteSummary(cleanRoute) {
        const analysis = cleanRoute.analysis;
        document.getElementById('cleanDistance').textContent = Utils.formatDistance(analysis.total_distance_km);
        document.getElementById('cleanAQI').textContent = analysis.average_aqi.toFixed(1);
        document.getElementById('cleanExposure').textContent = analysis.pollution_exposure.toFixed(1);
    }

    updateWaypointsList(waypoints) {
        const waypointsList = document.getElementById('waypointsList');
        
        // Show first 20 waypoints to avoid overwhelming the UI
        const displayWaypoints = waypoints.slice(0, 20);
        
        const html = displayWaypoints.map((wp, index) => {
            const category = Utils.getAQICategory(wp.aqi);
            return `
                <div class="waypoint-item">
                    <span class="waypoint-index">${index + 1}</span>
                    <span class="waypoint-coords">${wp.lat.toFixed(4)}, ${wp.lon.toFixed(4)}</span>
                    <span class="waypoint-aqi aqi-${category}">${wp.aqi.toFixed(1)}</span>
                </div>
            `;
        }).join('');
        
        const totalCount = waypoints.length;
        const message = totalCount > 20 
            ? `<div class="waypoints-note">Showing first 20 of ${totalCount} waypoints</div>` 
            : '';
        
        waypointsList.innerHTML = message + html;
    }
 
    async recalculateIfRoutesExist() {
        if (this.currentRoutes && this.startPoint && this.endPoint) {
            await this.calculateRoutes();
        }
    }
 
    clearAll() {
        // Clear points
        this.startPoint = null;
        this.endPoint = null;
        this.currentRoutes = null;
        this.selectedRoute = null;
        
        // Clear inputs
        document.getElementById('startInput').value = '';
        document.getElementById('endInput').value = '';
        
        // Clear map
        this.map.clearMarkers();
        
        // Reset UI
        this.resetUI();
    }
 
    clearRoutes() {
        this.currentRoutes = null;
        this.selectedRoute = null;
        this.map.clearRoutes();
        this.resetUI();
    }
 
    resetUI() {
        // Reset route summary
        document.getElementById('cleanDistance').textContent = '--';
        document.getElementById('cleanAQI').textContent = '--';
        document.getElementById('cleanExposure').textContent = '--';
        
        // Reset waypoints list
        document.getElementById('waypointsList').innerHTML = '<div class="loading">Calculate a route to see waypoints</div>';
    }

    viewRouteDetails() {
        if (!this.currentRoutes) {
            Utils.showError('Please calculate routes first to view details');
            return;
        }

        // Store route data in sessionStorage for the details page
        sessionStorage.setItem('routeData', JSON.stringify(this.currentRoutes));

        // Open the route details page in a new tab
        window.open('route-details.html', '_blank');
    }

    loadSavedRoutes() {
        try {
            const routes = this.storage.getAllRoutes();
            this.updateRoutesHistory(routes);
        } catch (error) {
            console.error('Error loading saved routes:', error);
        }
    }

    updateRoutesHistory(routes) {
        const routesHistory = document.getElementById('routesHistory');
        
        if (routes.length === 0) {
            routesHistory.innerHTML = '<div class="loading">No saved routes yet</div>';
            return;
        }

        const html = routes.map(route => {
            const date = this.storage.formatTimestamp(route.timestamp);
            return `
                <div class="route-history-item" data-route-id="${route.id}">
                    <div class="route-history-header">
                        <span class="route-history-date">${date}</span>
                        <div class="route-history-actions">
                            <button onclick="app.loadRoute('${route.id}')" title="Load Route">
                                <i class="fas fa-route"></i>
                            </button>
                            <button onclick="app.viewSavedRouteDetails('${route.id}')" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button onclick="app.deleteRoute('${route.id}')" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    <div class="route-history-stats">
                        <div class="route-stat">
                            <span class="route-stat-label">Clean Dist:</span>
                            <span class="route-stat-value clean">${Utils.formatDistance(route.metadata.cleanDistance)}</span>
                        </div>
                        <div class="route-stat">
                            <span class="route-stat-label">Clean AQI:</span>
                            <span class="route-stat-value clean">${route.metadata.cleanAQI.toFixed(1)}</span>
                        </div>
                        <div class="route-stat">
                            <span class="route-stat-label">Fast Dist:</span>
                            <span class="route-stat-value fast">${Utils.formatDistance(route.metadata.fastDistance)}</span>
                        </div>
                        <div class="route-stat">
                            <span class="route-stat-label">Fast AQI:</span>
                            <span class="route-stat-value fast">${route.metadata.fastAQI.toFixed(1)}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        routesHistory.innerHTML = html;
    }

    loadRoute(routeId) {
        try {
            const route = this.storage.getRouteById(routeId);
            if (!route) {
                Utils.showError('Route not found');
                return;
            }

            // Set start and end points
            this.setStartPoint(route.startPoint.lat, route.startPoint.lon);
            this.setEndPoint(route.endPoint.lat, route.endPoint.lon);

            // Display the route
            this.displayRoutes(route.data);
            
            Utils.showError('Route loaded successfully');
        } catch (error) {
            console.error('Error loading route:', error);
            Utils.showError('Failed to load route');
        }
    }

    viewSavedRouteDetails(routeId) {
        try {
            const route = this.storage.getRouteById(routeId);
            if (!route) {
                Utils.showError('Route not found');
                return;
            }

            // Store route data in sessionStorage for the details page
            sessionStorage.setItem('routeData', JSON.stringify(route.data));

            // Open the route details page in a new tab
            window.open('route-details.html', '_blank');
        } catch (error) {
            console.error('Error viewing route details:', error);
            Utils.showError('Failed to view route details');
        }
    }

    deleteRoute(routeId) {
        if (confirm('Are you sure you want to delete this route?')) {
            try {
                this.storage.deleteRoute(routeId);
                this.loadSavedRoutes();
                Utils.showError('Route deleted successfully');
            } catch (error) {
                console.error('Error deleting route:', error);
                Utils.showError('Failed to delete route');
            }
        }
    }

    exportRoutes() {
        try {
            const success = this.storage.exportRoutes();
            if (success) {
                Utils.showError('Routes exported successfully');
            } else {
                Utils.showError('Failed to export routes');
            }
        } catch (error) {
            console.error('Error exporting routes:', error);
            Utils.showError('Failed to export routes');
        }
    }

    importRoutes() {
        document.getElementById('importFileInput').click();
    }

    async handleImportFile(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            const count = await this.storage.importRoutes(file);
            this.loadSavedRoutes();
            Utils.showError(`Imported ${count} routes successfully`);
        } catch (error) {
            console.error('Error importing routes:', error);
            Utils.showError('Failed to import routes: ' + error.message);
        }

        // Reset file input
        event.target.value = '';
    }
}
 
// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AQIRouteApp();
});
