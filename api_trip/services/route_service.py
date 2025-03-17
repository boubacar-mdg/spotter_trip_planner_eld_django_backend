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