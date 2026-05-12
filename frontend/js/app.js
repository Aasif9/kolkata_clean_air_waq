// Main Application Controller
class AQIRouteApp {
    constructor() {
        this.api = new AQIAPI();
        this.map = new AQIMap();
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
        
        // Route selection buttons
        document.getElementById('showFastBtn').addEventListener('click', () => this.selectRoute('fast'));
        document.getElementById('showCleanBtn').addEventListener('click', () => this.selectRoute('clean'));
        
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
        
        // Update route cards
        this.updateRouteCards(data);
        
        // Update comparison
        this.updateComparison(data.comparison);
        
        // Select clean route by default
        this.selectRoute('clean');
    }
 
    updateRouteCards(data) {
        // Fast route
        const fastAnalysis = data.fast_route.analysis;
        document.getElementById('fastDistance').textContent = Utils.formatDistance(fastAnalysis.total_distance_km);
        document.getElementById('fastAQI').textContent = fastAnalysis.average_aqi.toFixed(1);
        
        // Clean route
        const cleanAnalysis = data.clean_route.analysis;
        document.getElementById('cleanDistance').textContent = Utils.formatDistance(cleanAnalysis.total_distance_km);
        document.getElementById('cleanAQI').textContent = cleanAnalysis.average_aqi.toFixed(1);
    }
 
    updateComparison(comparison) {
        // Update trade-off values
        const extraDistance = comparison.distance_increase_percent;
        const aqiImprovement = comparison.aqi_improvement;
        
        document.getElementById('extraDistance').textContent = `${extraDistance > 0 ? '+' : ''}${extraDistance.toFixed(1)}%`;
        document.getElementById('aqiImprovement').textContent = `${aqiImprovement > 0 ? '+' : ''}${aqiImprovement.toFixed(1)}`;
        
        // Generate recommendation
        const recommendation = Utils.generateRecommendation(
            this.currentRoutes.clean_route,
            this.currentRoutes.fast_route,
            comparison
        );
        
        document.getElementById('recommendationText').textContent = recommendation;
    }
 
    selectRoute(type) {
        if (!this.currentRoutes) return;
        
        this.selectedRoute = type;
        
        // Update map
        this.map.highlightRoute(type);
        
        // Update card styles
        document.getElementById('fastRouteCard').classList.toggle('active', type === 'fast');
        document.getElementById('cleanRouteCard').classList.toggle('active', type === 'clean');
    }
 
    updatePollutionDescription() {
        const factor = parseFloat(document.getElementById('pollutionSlider').value);
        document.getElementById('pollutionValue').textContent = factor.toFixed(1);
        document.getElementById('pollutionDescription').textContent = Utils.getPollutionDescription(factor);
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
        // Reset route cards
        document.getElementById('fastDistance').textContent = '--';
        document.getElementById('fastAQI').textContent = '--';
        document.getElementById('cleanDistance').textContent = '--';
        document.getElementById('cleanAQI').textContent = '--';
        
        // Reset comparison
        document.getElementById('extraDistance').textContent = '--';
        document.getElementById('aqiImprovement').textContent = '--';
        document.getElementById('recommendationText').textContent = 'Select start and end points to see recommendations';
        
        // Reset card active states
        document.getElementById('fastRouteCard').classList.remove('active');
        document.getElementById('cleanRouteCard').classList.remove('active');
    }
}
 
// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AQIRouteApp();
});
