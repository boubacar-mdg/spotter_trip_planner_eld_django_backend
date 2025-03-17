import requests
import datetime
import os

OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY", default="")

class RouteService:
    def __init__(self):
        self.osrm_base_url = "http://router.project-osrm.org/route/v1/driving"
        self.geocode_base_url = "https://api.opencagedata.com/geocode/v1/json"
        self.api_key = OPENCAGE_API_KEY
        

    def geocode(self, givenLocation):
        """Helper function to get geocode (long,lat) for given location"""

        params = {"q": givenLocation, "key": self.api_key, "limit": 1}

        url = self.geocode_base_url

        print(f"Requesting URL: {url}?q={givenLocation}&key={self.api_key}")

        response = requests.get(url, params=params)

        data = response.json()

        if data and data["results"]:
            result = data["results"][0]
            geocode = {
                "lat": result["geometry"]["lat"],
                "lon": result["geometry"]["lng"],
                "display_name": result["formatted"],
            }
            print(f"Geocode: {geocode}")
            return geocode
        return None
    
    
    def get_route(self, start_coords, end_coords):
        """Get route details between two given coordinates"""
        url = f"{self.osrm_base_url}/{start_coords['lon']},{start_coords['lat']};{end_coords['lon']},{end_coords['lat']}"
        print(f"Url for getting route beetwen the start and end coordinates: {url}")
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'true'
        }
        response = requests.get(url, params=params)
        route = response.json()
        """  print(f"Route: {route}") """
        return route
    
    def determine_routes_and_stops(self, trip):
        """Dertermine complete route with stops"""
       
        current_location = self.geocode(trip.current_location)
        pickup_location = self.geocode(trip.pickup_location)
        dropoff_location = self.geocode(trip.dropoff_location)
        
        if not all([current_location, pickup_location, dropoff_location]):
            return {"error": "Failed to get address geo details for one or more locations"}
        
        routesFromCurrentLocationToPickupLocation = self.get_route(current_location, pickup_location)
        routesFromPickupLocationToDropoffLocation = self.get_route(pickup_location, dropoff_location)
        
        route_details = self._determine_routes(routesFromCurrentLocationToPickupLocation, routesFromPickupLocationToDropoffLocation)
        
        # TODO: Determine stops
        stops = {}
        
        return {
            "route_details": route_details,
            "stops": stops
        }
        
        
    def _determine_routes(self, routesFromCurrentLocationToPickupLocation, routesFromPickupLocationToDropoffLocation):
        """Process route data from OSRM"""
        # In a real app, you'd do more processing here
        pickup_route = routesFromCurrentLocationToPickupLocation['routes'][0]
        dropoff_route = routesFromPickupLocationToDropoffLocation['routes'][0]
        
        # Calculate total distance and duration
        pickup_distance = pickup_route['distance'] / 1000  # km to miles (approximate)
        pickup_duration = pickup_route['duration'] / 3600  # seconds to hours
        
        dropoff_distance = dropoff_route['distance'] / 1000  # km to miles (approximate)
        dropoff_duration = dropoff_route['duration'] / 3600  # seconds to hours
        
        # Combine route geometries
        combined_geometry = {
            "pickup_route": pickup_route['geometry'],
            "dropoff_route": dropoff_route['geometry']
        }
        
        route_data = {
            "total_distance": pickup_distance + dropoff_distance,
            "total_duration": pickup_duration + dropoff_duration,
            "pickup_distance": pickup_distance,
            "pickup_duration": pickup_duration,
            "dropoff_distance": dropoff_distance,
            "dropoff_duration": dropoff_duration,
            "geometry": combined_geometry
        }
        
        print(f"Logging route data ${route_data}")
        
        return route_data