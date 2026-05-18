// LocalStorage Service for Route Data
class RouteStorage {
    constructor() {
        this.storageKey = 'kolkata_aqi_routes';
        this.maxRoutes = 50; // Maximum number of routes to store
    }

    // Save a route with metadata
    saveRoute(routeData, startPoint, endPoint) {
        try {
            const routes = this.getAllRoutes();
            
            const newRoute = {
                id: this.generateId(),
                timestamp: new Date().toISOString(),
                startPoint: startPoint,
                endPoint: endPoint,
                data: routeData,
                metadata: {
                    cleanDistance: routeData.clean_route.analysis.total_distance_km,
                    cleanAQI: routeData.clean_route.analysis.average_aqi,
                    fastDistance: routeData.fast_route.analysis.total_distance_km,
                    fastAQI: routeData.fast_route.analysis.average_aqi,
                    distanceIncrease: routeData.comparison.distance_increase_percent,
                    aqiImprovement: routeData.comparison.aqi_improvement
                }
            };
            
            // Add new route to beginning of array
            routes.unshift(newRoute);
            
            // Keep only the most recent routes
            if (routes.length > this.maxRoutes) {
                routes.splice(this.maxRoutes);
            }
            
            localStorage.setItem(this.storageKey, JSON.stringify(routes));
            console.log('Route saved successfully:', newRoute.id);
            return newRoute.id;
        } catch (error) {
            console.error('Error saving route:', error);
            throw new Error('Failed to save route: ' + error.message);
        }
    }

    // Get all saved routes
    getAllRoutes() {
        try {
            const data = localStorage.getItem(this.storageKey);
            return data ? JSON.parse(data) : [];
        } catch (error) {
            console.error('Error reading routes:', error);
            return [];
        }
    }

    // Get a specific route by ID
    getRouteById(id) {
        try {
            const routes = this.getAllRoutes();
            return routes.find(route => route.id === id) || null;
        } catch (error) {
            console.error('Error getting route:', error);
            return null;
        }
    }

    // Delete a route by ID
    deleteRoute(id) {
        try {
            const routes = this.getAllRoutes();
            const filteredRoutes = routes.filter(route => route.id !== id);
            localStorage.setItem(this.storageKey, JSON.stringify(filteredRoutes));
            console.log('Route deleted:', id);
            return true;
        } catch (error) {
            console.error('Error deleting route:', error);
            return false;
        }
    }

    // Clear all saved routes
    clearAllRoutes() {
        try {
            localStorage.removeItem(this.storageKey);
            console.log('All routes cleared');
            return true;
        } catch (error) {
            console.error('Error clearing routes:', error);
            return false;
        }
    }

    // Export all routes as JSON
    exportRoutes() {
        try {
            const routes = this.getAllRoutes();
            const dataStr = JSON.stringify(routes, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `kolkata_aqi_routes_${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            
            URL.revokeObjectURL(url);
            console.log('Routes exported successfully');
            return true;
        } catch (error) {
            console.error('Error exporting routes:', error);
            return false;
        }
    }

    // Import routes from JSON file
    async importRoutes(file) {
        try {
            const text = await file.text();
            const importedRoutes = JSON.parse(text);
            
            if (!Array.isArray(importedRoutes)) {
                throw new Error('Invalid file format');
            }

            const existingRoutes = this.getAllRoutes();
            const mergedRoutes = [...importedRoutes, ...existingRoutes];
            
            // Remove duplicates by ID
            const uniqueRoutes = mergedRoutes.filter((route, index, self) =>
                index === self.findIndex(r => r.id === route.id)
            );
            
            // Sort by timestamp (newest first)
            uniqueRoutes.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            // Keep only the most recent routes
            if (uniqueRoutes.length > this.maxRoutes) {
                uniqueRoutes.splice(this.maxRoutes);
            }
            
            localStorage.setItem(this.storageKey, JSON.stringify(uniqueRoutes));
            console.log(`Imported ${importedRoutes.length} routes`);
            return importedRoutes.length;
        } catch (error) {
            console.error('Error importing routes:', error);
            throw new Error('Failed to import routes: ' + error.message);
        }
    }

    // Get storage statistics
    getStorageStats() {
        try {
            const routes = this.getAllRoutes();
            const dataStr = localStorage.getItem(this.storageKey);
            const sizeInBytes = dataStr ? new Blob([dataStr]).size : 0;
            const sizeInKB = (sizeInBytes / 1024).toFixed(2);
            
            return {
                totalRoutes: routes.length,
                storageUsed: sizeInKB + ' KB',
                oldestRoute: routes.length > 0 ? routes[routes.length - 1].timestamp : null,
                newestRoute: routes.length > 0 ? routes[0].timestamp : null
            };
        } catch (error) {
            console.error('Error getting storage stats:', error);
            return null;
        }
    }

    // Generate unique ID
    generateId() {
        return 'route_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // Format timestamp for display
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// Export for use in other modules
window.RouteStorage = RouteStorage;
