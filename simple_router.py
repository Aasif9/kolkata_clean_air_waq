import networkx as nx
import numpy as np
from geopy.distance import geodesic
 
class SimplePollutionRouter:
    def __init__(self, graph, aqi_interpolator, pollution_factor=3.0):
        self.graph = graph
        self.aqi_interpolator = aqi_interpolator
        self.pollution_factor = pollution_factor

    def get_pollution_penalty(self, aqi: float, factor: float = None) -> float:
        """
        Calculate pollution penalty based on AQI value
        Tuned for Indian AQI range (50-150)

        Args:
            aqi: AQI value
            factor: Pollution factor (uses instance default if not provided)

        Returns:
            Penalty multiplier
        """
        if factor is None:
            factor = self.pollution_factor

        if aqi <= 50:
            return 1.0
        elif aqi <= 100:
            return 1.0 + factor * (aqi - 50) / 80.0
        else:
            return 1.0 + factor * (aqi - 50) / 50.0  # stronger penalty above 100
    
    def find_fastest_path(self, start_lat, start_lon, end_lat, end_lon):
        """Find fastest path using Dijkstra on travel time"""
        try:
            # Find nearest graph nodes
            start_node = self._find_graph_node(start_lat, start_lon)
            end_node = self._find_graph_node(end_lat, end_lon)
            
            # Find shortest path by travel time
            path = nx.shortest_path(
                self.graph, 
                source=start_node, 
                target=end_node, 
                weight='travel_time'
            )
            
            return path
            
        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            print(f"No path found: {e}")
            return None
    
    def find_cleanest_path(self, start_lat, start_lon, end_lat, end_lon):
        """Find cleanest path considering pollution using direct exposure minimization"""
        try:
            # Find nearest graph nodes
            start_node = self._find_graph_node(start_lat, start_lon)
            end_node = self._find_graph_node(end_lat, end_lon)

            # Create custom weight function - direct exposure minimization
            def pollution_weight(u, v, d):
                # Base travel time
                travel_time = d.get('travel_time', 1)

                # Get coordinates for edge midpoint
                u_data = self.graph.nodes[u]
                v_data = self.graph.nodes[v]
                mid_lat = (u_data['y'] + v_data['y']) / 2
                mid_lon = (u_data['x'] + v_data['x']) / 2

                # Get AQI at midpoint
                aqi = self.aqi_interpolator.get_aqi_at_point(mid_lat, mid_lon)

                # Use improved pollution penalty function
                penalty = self.get_pollution_penalty(aqi)

                # Option B (Recommended): Direct exposure minimization
                # This directly minimizes AQI exposure rather than time-penalty
                return travel_time * penalty

            # Find path with pollution weights
            path = nx.shortest_path(
                self.graph,
                source=start_node,
                target=end_node,
                weight=pollution_weight
            )

            return path

        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            print(f"No clean path found: {e}")
            return None
    
    def _find_graph_node(self, lat, lon):
        """Find nearest graph node to coordinates"""
        # Simple nearest node search
        min_dist = float('inf')
        nearest_node = None
        
        for node in self.graph.nodes():
            node_data = self.graph.nodes[node]
            node_lat = node_data['y']
            node_lon = node_data['x']
            
            # Calculate distance
            distance = geodesic((lat, lon), (node_lat, node_lon)).meters
            
            if distance < min_dist:
                min_dist = distance
                nearest_node = node
        
        return nearest_node
    
    def analyze_path_pollution(self, path):
        """Analyze pollution levels along a path"""
        if not path or len(path) < 2:
            return {
                'total_distance_km': 0,
                'total_travel_time_min': 0,
                'average_aqi': 85,
                'length_weighted_average_aqi': 85,
                'max_aqi': 85,
                'min_aqi': 85,
                'pollution_exposure': 0,
                'total_exposure': 0,
                'exposure_per_km': 0,
                'aqi_category_percentages': {
                    'good': 0,
                    'moderate': 0,
                    'unhealthy_for_sensitive_groups': 0,
                    'unhealthy': 0,
                    'very_unhealthy': 0,
                    'hazardous': 0
                },
                'aqi_samples': 0
            }
        
        total_distance = 0.0
        total_travel_time = 0.0
        aqi_values = []
        distance_weighted_aqi_sum = 0.0
        total_exposure = 0.0
        category_distances = {
            'good': 0.0,
            'moderate': 0.0,
            'unhealthy_for_sensitive_groups': 0.0,
            'unhealthy': 0.0,
            'very_unhealthy': 0.0,
            'hazardous': 0.0
        }
        
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            
            # Get node data
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]
            
            # Calculate distance
            distance = geodesic(
                (u_data['y'], u_data['x']),
                (v_data['y'], v_data['x'])
            ).kilometers
            
            # Get edge data
            edge_data = self.graph.get_edge_data(u, v)
            if edge_data:
                # Use first edge (there might be multiple parallel edges)
                edge = list(edge_data.values())[0]
                travel_time = edge.get('travel_time', distance * 2)  # Default 30 km/h
            else:
                travel_time = distance * 2  # Default assumption
            
            # Get AQI at edge midpoint
            mid_lat = (u_data['y'] + v_data['y']) / 2
            mid_lon = (u_data['x'] + v_data['x']) / 2
            aqi = self.aqi_interpolator.get_aqi_at_point(mid_lat, mid_lon)
            
            total_distance += distance
            total_travel_time += travel_time
            aqi_values.append(aqi)
            distance_weighted_aqi_sum += aqi * distance
            total_exposure += aqi * travel_time
            category_distances[self._get_aqi_category(aqi)] += distance
        
        # Calculate statistics
        average_aqi = np.mean(aqi_values) if aqi_values else 85
        max_aqi = np.max(aqi_values) if aqi_values else 85
        min_aqi = np.min(aqi_values) if aqi_values else 85
        length_weighted_average_aqi = distance_weighted_aqi_sum / total_distance if total_distance > 0 else average_aqi
        pollution_exposure = total_distance * average_aqi  # km * AQI
        exposure_per_km = total_exposure / total_distance if total_distance > 0 else 0
        aqi_category_percentages = {
            category: (distance / total_distance * 100) if total_distance > 0 else 0
            for category, distance in category_distances.items()
        }
        
        return {
            'total_distance_km': total_distance,
            'total_travel_time_min': total_travel_time,
            'average_aqi': average_aqi,
            'length_weighted_average_aqi': length_weighted_average_aqi,
            'max_aqi': max_aqi,
            'min_aqi': min_aqi,
            'pollution_exposure': pollution_exposure,
            'total_exposure': total_exposure,
            'exposure_per_km': exposure_per_km,
            'aqi_category_percentages': aqi_category_percentages,
            'aqi_samples': len(aqi_values)
        }

    def _get_aqi_category(self, aqi):
        if aqi <= 50:
            return 'good'
        elif aqi <= 100:
            return 'moderate'
        elif aqi <= 150:
            return 'unhealthy_for_sensitive_groups'
        elif aqi <= 200:
            return 'unhealthy'
        elif aqi <= 300:
            return 'very_unhealthy'
        else:
            return 'hazardous'
    
    def compare_routes(self, start_lat, start_lon, end_lat, end_lon):
        """Compare clean vs fast routes"""
        # Find both routes
        fast_path = self.find_fastest_path(start_lat, start_lon, end_lat, end_lon)
        clean_path = self.find_cleanest_path(start_lat, start_lon, end_lat, end_lon)
        
        if not fast_path or not clean_path:
            return None
        
        # Analyze both routes
        fast_analysis = self.analyze_path_pollution(fast_path)
        clean_analysis = self.analyze_path_pollution(clean_path)
        
        # Calculate comparison metrics
        distance_increase = (
            (clean_analysis['total_distance_km'] - fast_analysis['total_distance_km']) 
            / fast_analysis['total_distance_km'] * 100
        )
        
        time_increase = (
            (clean_analysis['total_travel_time_min'] - fast_analysis['total_travel_time_min'])
            / fast_analysis['total_travel_time_min'] * 100
        )
        
        aqi_improvement = fast_analysis['average_aqi'] - clean_analysis['average_aqi']
        exposure_reduction = fast_analysis['pollution_exposure'] - clean_analysis['pollution_exposure']
        
        return {
            'fast_route': {
                'path': fast_path,
                'analysis': fast_analysis
            },
            'clean_route': {
                'path': clean_path,
                'analysis': clean_analysis
            },
            'comparison': {
                'distance_increase_percent': distance_increase,
                'time_increase_percent': time_increase,
                'aqi_improvement': aqi_improvement,
                'exposure_reduction': exposure_reduction
            }
        }
 
def test_router():
    """Test the pollution router with real AQI data"""
    from aqi_service import AQIInterpolator
    import pickle
    
    # Load network
    try:
        with open('kolkata_road_network.pkl', 'rb') as f:
            graph = pickle.load(f)
        print("Loaded road network")
    except FileNotFoundError:
        print("Network not found. Run basic_network.py first!")
        return
    
    # Load AQI interpolator with real data
    try:
        interpolator = AQIInterpolator()
        print("Loaded real AQI interpolator")
    except Exception as e:
        print(f"Failed to load AQI interpolator: {e}")
        return
    
    # Create router
    router = SimplePollutionRouter(graph, interpolator)
    
    # Test routes
    test_cases = [
        {
            'name': 'Howrah to Salt Lake',
            'start': (22.5750, 88.3500),
            'end': (22.5800, 88.3800)
        },
        {
            'name': 'Park Street to Dum Dum',
            'start': (22.5620, 88.3500),
            'end': (22.5850, 88.3700)
        }
    ]
    
    print("\n=== Pollution Routing Test ===")
    for case in test_cases:
        print(f"\nTesting: {case['name']}")
        
        comparison = router.compare_routes(
            case['start'][0], case['start'][1],
            case['end'][0], case['end'][1]
        )
        
        if comparison:
            fast = comparison['fast_route']['analysis']
            clean = comparison['clean_route']['analysis']
            comp = comparison['comparison']
            
            print(f"  Fast route: {fast['total_distance_km']:.2f}km, {fast['total_travel_time_min']:.1f}min, AQI {fast['average_aqi']:.1f}")
            print(f"  Clean route: {clean['total_distance_km']:.2f}km, {clean['total_travel_time_min']:.1f}min, AQI {clean['average_aqi']:.1f}")
            print(f"  Trade-off: +{comp['distance_increase_percent']:.1f}% distance, -{comp['aqi_improvement']:.1f} AQI")
        else:
            print("  No route found")
    
    return router

if __name__ == "__main__":
    test_router()
