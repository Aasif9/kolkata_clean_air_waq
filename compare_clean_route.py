import argparse
import pickle

from aqi_service import AQIInterpolator
from simple_router import SimplePollutionRouter


def print_route_metrics(label, route):
    analysis = route["analysis"]
    print(f"\n{label}")
    print("-" * len(label))
    print(f"Distance: {analysis['total_distance_km']:.2f} km")
    print(f"Time: {analysis['total_travel_time_min']:.2f} min")
    print(f"Avg AQI: {analysis['average_aqi']:.2f}")
    print(f"Length-weighted Avg AQI: {analysis.get('length_weighted_average_aqi', analysis['average_aqi']):.2f}")
    print(f"Min AQI: {analysis['min_aqi']:.2f}")
    print(f"Max AQI: {analysis['max_aqi']:.2f}")
    print(f"Total Exposure: {analysis.get('total_exposure', analysis['pollution_exposure']):.2f}")
    print(f"Exposure/km: {analysis.get('exposure_per_km', 0):.2f}")
    print(f"Waypoints: {route['node_count']}")

    categories = analysis.get("aqi_category_percentages")
    if categories:
        print("AQI category % by route length:")
        for category, percent in categories.items():
            print(f"  {category}: {percent:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Compare fastest and cleanest AQI routes.")
    parser.add_argument("--start-lat", type=float, required=True)
    parser.add_argument("--start-lon", type=float, required=True)
    parser.add_argument("--end-lat", type=float, required=True)
    parser.add_argument("--end-lon", type=float, required=True)
    parser.add_argument("--pollution-factor", type=float, default=3.0)
    args = parser.parse_args()

    with open("kolkata_road_network.pkl", "rb") as f:
        graph = pickle.load(f)

    interpolator = AQIInterpolator()
    router = SimplePollutionRouter(graph, interpolator, pollution_factor=args.pollution_factor)

    fast_path = router.find_fastest_path(args.start_lat, args.start_lon, args.end_lat, args.end_lon)
    clean_path = router.find_cleanest_path(args.start_lat, args.start_lon, args.end_lat, args.end_lon)

    if not fast_path:
        print("Fast route not found. Try coordinates inside the current road-network area.")
        return

    if not clean_path:
        print("Clean route not found. Try coordinates inside the current road-network area.")
        return

    fast_route = {
        "node_count": len(fast_path),
        "analysis": router.analyze_path_pollution(fast_path),
    }
    clean_route = {
        "node_count": len(clean_path),
        "analysis": router.analyze_path_pollution(clean_path),
    }

    print("Clean Route Change Test")
    print("=======================")
    print(f"Start: ({args.start_lat}, {args.start_lon})")
    print(f"End: ({args.end_lat}, {args.end_lon})")
    print(f"Pollution factor: {args.pollution_factor}")

    print_route_metrics("FASTEST ROUTE", fast_route)
    print_route_metrics("CLEANEST ROUTE", clean_route)

    fast = fast_route["analysis"]
    clean = clean_route["analysis"]

    distance_change = ((clean["total_distance_km"] - fast["total_distance_km"]) / fast["total_distance_km"] * 100) if fast["total_distance_km"] else 0
    time_change = ((clean["total_travel_time_min"] - fast["total_travel_time_min"]) / fast["total_travel_time_min"] * 100) if fast["total_travel_time_min"] else 0
    exposure_reduction = fast.get("total_exposure", 0) - clean.get("total_exposure", 0)
    exposure_reduction_percent = (exposure_reduction / fast.get("total_exposure", 1) * 100) if fast.get("total_exposure", 0) else 0

    print("\nCOMPARISON")
    print("----------")
    print(f"Distance change: {distance_change:+.2f}%")
    print(f"Time change: {time_change:+.2f}%")
    print(f"Avg AQI improvement: {fast['average_aqi'] - clean['average_aqi']:.2f}")
    print(f"Exposure reduction: {exposure_reduction:.2f} ({exposure_reduction_percent:.2f}%)")

    if exposure_reduction > 0:
        print("\nResult: Clean route reduced exposure.")
    else:
        print("\nResult: Clean route did not reduce exposure for this coordinate pair. Try a route crossing higher-AQI areas or increase --pollution-factor.")


if __name__ == "__main__":
    main()
