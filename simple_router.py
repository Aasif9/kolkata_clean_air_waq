import networkx as nx
import numpy as np
from geopy.distance import geodesic
from dummy_aqi_interpolator import DummyAQIInterpolator
 
class SimplePollutionRouter:
    def __init__(self, graph, aqi_interpolator, pollution_factor=2.0):
        self.graph = graph
        self.aqi_interpolator = aqi_interpolator
        self.pollution_factor = pollution_factor
    
    def find_fastest_path(self, start_lat, start_lon, end_lat, end_lon):
        """Find fastest path using Dijkstra on travel time"""
        try:
            # Find nearest nodes
            start_node = self.aqi_interpolator._nearest_neighbor(start_lat, start_lon)
            end_node = self.aqi_interpolator._nearest_neighbor(end_lat, end_lon)
            
            # Convert to actual graph nodes
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
        """Find cleanest path considering pollution"""
        try:
            # Find nearest graph nodes
            start_node = self._find_graph_node(start_lat, start_lon)
            end_node = self._find_graph_node(end_lat, end_lon)
            
            # Create custom weight function
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
                
                # Calculate pollution penalty
                pollution_penalty = 1 + (self.pollution_factor * (aqi / 100))
                
                # Return weighted travel time
                return travel_time * pollution_penalty
            
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
                'max_aqi': 85,
                'min_aqi': 85,
                'pollution_exposure': 0
            }
        
        total_distance = 0.0
        total_travel_time = 0.0
        aqi_values = []
        
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
        
        # Calculate statistics
        average_aqi = np.mean(aqi_values) if aqi_values else 85
        max_aqi = np.max(aqi_values) if aqi_values else 85
        min_aqi = np.min(aqi_values) if aqi_values else 85
        pollution_exposure = total_distance * average_aqi  # km * AQI
        
        return {
            'total_distance_km': total_distance,
            'total_travel_time_min': total_travel_time,
            'average_aqi': average_aqi,
            'max_aqi': max_aqi,
            'min_aqi': min_aqi,
            'pollution_exposure': pollution_exposure,
            'aqi_samples': len(aqi_values)
        }
    
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
    """Test the pollution router"""
    from basic_network import KolkataRoadNetwork
    import pickle
    
    # Load network
    try:
        with open('kolkata_road_network.pkl', 'rb') as f:
            graph = pickle.load(f)
        print("Loaded road network")
    except FileNotFoundError:
        print("Network not found. Run basic_network.py first!")
        return
    
    # Load AQI interpolator
    interpolator = DummyAQIInterpolator()
    if not interpolator.stations:
        print("No AQI stations found. Run dummy_aqi_generator.py first!")
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
