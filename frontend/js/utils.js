// Utility Functions
const Utils = {
    // Format coordinates
    formatCoordinates(lat, lon) {
        return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    },
 
    // Parse coordinates from string
    parseCoordinates(coordString) {
        const parts = coordString.split(',');
        if (parts.length !== 2) return null;
        
        const lat = parseFloat(parts[0].trim());
        const lon = parseFloat(parts[1].trim());
        
        if (isNaN(lat) || isNaN(lon)) return null;
        
        return { lat, lon };
    },
 
    // Calculate distance between two points (Haversine)
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in km
        const dLat = this.toRadians(lat2 - lat1);
        const dLon = this.toRadians(lon2 - lon1);
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    },
 
    toRadians(degrees) {
        return degrees * (Math.PI / 180);
    },
 
    // Get AQI color
    getAQIColor(aqi) {
        if (aqi <= 50) return '#2ecc71';      // Good - Green
        if (aqi <= 100) return '#f39c12';     // Moderate - Yellow
        if (aqi <= 150) return '#e67e22';     // Unhealthy for sensitive - Orange
        if (aqi <= 200) return '#e74c3c';     // Unhealthy - Red
        return '#8e44ad';                      // Very Unhealthy - Purple
    },
 
    // Get AQI category
    getAQICategory(aqi) {
        if (aqi <= 50) return 'good';
        if (aqi <= 100) return 'moderate';
        if (aqi <= 150) return 'unhealthy';
        return 'very-unhealthy';
    },
 
    // Get AQI description
    getAQIDescription(aqi) {
        if (aqi <= 50) return 'Good';
        if (aqi <= 100) return 'Moderate';
        if (aqi <= 150) return 'Unhealthy for Sensitive Groups';
        if (aqi <= 200) return 'Unhealthy';
        return 'Very Unhealthy';
    },
 
    // Format distance
    formatDistance(km) {
        if (km < 1) {
            return `${(km * 1000).toFixed(0)}m`;
        }
        return `${km.toFixed(2)}km`;
    },
 
    // Show error message
    showError(message) {
        const errorToast = document.getElementById('errorToast');
        const errorMessage = document.getElementById('errorMessage');
        
        errorMessage.textContent = message;
        errorToast.classList.add('active');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorToast.classList.remove('active');
        }, 5000);
    },
 
    // Show/hide loading
    setLoading(isLoading) {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (isLoading) {
            loadingOverlay.classList.add('active');
        } else {
            loadingOverlay.classList.remove('active');
        }
    },
 
    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
 
    // Pollution factor descriptions
    getPollutionDescription(factor) {
        if (factor <= 1) return 'Minimal pollution avoidance - prioritize speed';
        if (factor <= 3) return 'Balanced routing with moderate pollution avoidance';
        if (factor <= 6) return 'Strong pollution avoidance - longer but cleaner routes';
        return 'Maximum pollution avoidance - significantly longer but cleanest routes';
    },
 
    // Generate recommendation based on route comparison
    generateRecommendation(cleanRoute, fastRoute, comparison) {
        const extraDistance = comparison.distance_increase_percent;
        const aqiImprovement = comparison.aqi_improvement;
        
        if (extraDistance < 5 && aqiImprovement > 10) {
            return 'Clean route recommended - minimal extra distance for significant air quality improvement';
        }
        
        if (extraDistance > 20 && aqiImprovement < 5) {
            return 'Fast route recommended - clean route is much longer with minimal air quality benefit';
        }
        
        if (extraDistance < 10 && aqiImprovement > 5) {
            return 'Clean route recommended - good balance between distance and air quality';
        }
        
        if (extraDistance > 15) {
            return 'Fast route recommended - clean route adds significant travel time';
        }
        
        return 'Both routes offer reasonable options - choose based on your priority';
    }
};
 
// Export for use in other modules
window.Utils = Utils;
