import osmnx as ox
import pickle
import networkx as nx
from geopy.distance import geodesic
 
class KolkataRoadNetwork:
    def __init__(self):
        # Kolkata center coordinates
        self.center_lat = 22.5726
        self.center_lon = 88.3639
        
        # 15km square region (7.5km in each direction from center)
        self.lat_range = 0.0675  # ~7.5km in latitude
        self.lon_range = 0.0675  # ~7.5km in longitude
        
        # Network bounds
        self.north = self.center_lat + self.lat_range
        self.south = self.center_lat - self.lat_range
        self.east = self.center_lon + self.lon_range
        self.west = self.center_lon - self.lon_range
        
        self.graph = None
    
    def download_network(self, network_type='drive'):
        """Download road network for Kolkata region"""
        print(f"Downloading {network_type} network for Kolkata region...")
        print(f"Bounds: {self.south:.4f} to {self.north:.4f}°N, {self.west:.4f} to {self.east:.4f}°E")
        
        # Download network
        self.graph = ox.graph_from_bbox(
            self.north, self.south, self.east, self.west,
            network_type=network_type,
            simplify=True,
            retain_all=True
        )
        
        # Add edge weights (travel time in minutes)
        self.graph = ox.add_edge_speeds(self.graph)
        self.graph = ox.add_edge_travel_times(self.graph)
        
        print(f"Downloaded network: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
        
        return self.graph
    
    def find_nearest_node(self, lat, lon):
        """Find nearest graph node to given coordinates"""
        if self.graph is None:
            raise ValueError("Network not loaded. Call download_network() first.")
        
        return ox.nearest_nodes(self.graph, lat, lon)
    
    def calculate_path_distance(self, path):
        """Calculate total distance of a path in kilometers"""
        if not path or len(path) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(path) - 1):
            node1 = self.graph.nodes[path[i]]
            node2 = self.graph.nodes[path[i + 1]]
            
            # Calculate geodesic distance
            distance = geodesic(
                (node1['y'], node1['x']),
                (node2['y'], node2['x'])
            ).kilometers
            
            total_distance += distance
        
        return total_distance
    
    def save_network(self, filename='kolkata_road_network.pkl'):
        """Save network to file"""
        if self.graph is None:
            raise ValueError("No network to save")
        
        with open(filename, 'wb') as f:
            pickle.dump(self.graph, f)
        
        print(f"Network saved to {filename}")
        print(f"Nodes: {len(self.graph.nodes)}, Edges: {len(self.graph.edges)}")
    
    def load_network(self, filename='kolkata_road_network.pkl'):
        """Load network from file"""
        try:
            with open(filename, 'rb') as f:
                self.graph = pickle.load(f)
            
            print(f"Network loaded from {filename}")
            print(f"Nodes: {len(self.graph.nodes)}, Edges: {len(self.graph.edges)}")
            return True
            
        except FileNotFoundError:
            print(f"Network file {filename} not found")
            return False
    
    def get_network_stats(self):
        """Get network statistics"""
        if self.graph is None:
            return "No network loaded"
        
        stats = {
            'nodes': len(self.graph.nodes),
            'edges': len(self.graph.edges),
            'bounds': {
                'north': self.north,
                'south': self.south,
                'east': self.east,
                'west': self.west
            }
        }
        
        # Calculate network density
        area_km2 = (2 * self.lat_range * 111) * (2 * self.lon_range * 111)  # Approximate
        stats['area_km2'] = area_km2
        stats['node_density'] = stats['nodes'] / area_km2
        stats['edge_density'] = stats['edges'] / area_km2
        
        return stats

def create_and_save_network():
    """Create and save Kolkata road network"""
    network = KolkataRoadNetwork()
    
    # Download network
    graph = network.download_network(network_type='drive')
    
    # Save network
    network.save_network()
    
    # Show stats
    stats = network.get_network_stats()
    print(f"\n=== Network Statistics ===")
    print(f"Area: {stats['area_km2']:.2f} km²")
    print(f"Nodes: {stats['nodes']} ({stats['node_density']:.1f} nodes/km²)")
    print(f"Edges: {stats['edges']} ({stats['edge_density']:.1f} edges/km²)")
    print(f"Bounds: {stats['bounds']['south']:.4f} to {stats['bounds']['north']:.4f}°N")
    print(f"Bounds: {stats['bounds']['west']:.4f} to {stats['bounds']['east']:.4f}°E")
    
    return network

if __name__ == "__main__":
    # Create and save network
    network = create_and_save_network()
