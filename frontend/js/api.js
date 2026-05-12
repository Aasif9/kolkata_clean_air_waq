// API Communication Module
class AQIAPI {
    constructor(baseURL = 'http://localhost:5002') {
        this.baseURL = baseURL;
        this.timeout = 10000; // 10 seconds timeout
    }
 
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
 
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }
 
    async getSystemStatus() {
        try {
            const response = await this.request('/');
            return { status: 'online', message: response };
        } catch (error) {
            return { status: 'offline', error: error.message };
        }
    }
 
    async getStations() {
        try {
            return await this.request('/stations');
        } catch (error) {
            throw new Error(`Failed to fetch AQI stations: ${error.message}`);
        }
    }
 
    async getCleanRoute(startLat, startLon, endLat, endLon, pollutionFactor = 2.0) {
        const params = new URLSearchParams({
            start_lat: startLat,
            start_lon: startLon,
            end_lat: endLat,
            end_lon: endLon,
            pollution_factor: pollutionFactor
        });
 
        try {
            return await this.request(`/routes/clean?${params}`);
        } catch (error) {
            throw new Error(`Failed to calculate routes: ${error.message}`);
        }
    }
 
    async testConnection() {
        const startTime = Date.now();
        try {
            await this.getSystemStatus();
            return {
                success: true,
                responseTime: Date.now() - startTime
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                responseTime: Date.now() - startTime
            };
        }
    }
}
 
// Export for use in other modules
window.AQIAPI = AQIAPI;
