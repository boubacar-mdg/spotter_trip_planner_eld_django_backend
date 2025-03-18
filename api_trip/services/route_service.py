import requests
import datetime
import os
from ..enums import StopType
from ..models import RouteStop, ELDLog
from api_trip.services.eld_service import ELDService

OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY", default="")

class RouteService:
    def __init__(self):
        self.osrm_base_url = "http://router.project-osrm.org/route/v1/driving"
        self.geocode_base_url = "https://api.opencagedata.com/geocode/v1/json"
        self.api_key = OPENCAGE_API_KEY
        self.add_time_for_pickup = 1
        self.add_time_for_dropoff = 1
        self.add_time_for_fuel_stop = 0.5
        self.add_time_for_rest_stop = 10
        

    def geocode(self, givenLocation):
        """Helper function to get geocode (long,lat) for given location"""

        params = {"q": givenLocation, "key": self.api_key, "limit": 1}

        url = self.geocode_base_url

        print(f"Geocode request URL => {url}?q={givenLocation}&key={self.api_key}")

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
        print(f"Url for getting route details beetwen the start and end coordinates => {url}")
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
        
        routes_from_current_location_to_pickup_location = self.get_route(current_location, pickup_location)
        routes_from_pickup_location_to_dropoff_location = self.get_route(pickup_location, dropoff_location)
        
        route_details = self._determine_routes(routes_from_current_location_to_pickup_location, routes_from_pickup_location_to_dropoff_location)
        
        # TODO: Determine stops
        stops = self._determine_stops(trip, route_details)
        
        for stop_data in stops:
            RouteStop.objects.create(
                trip=trip,
                location=stop_data['location'],
                arrival_time=stop_data['arrival_time'],
                departure_time=stop_data['departure_time'],
                stop_type=stop_data['stop_type']
            )
            
        
        eld_service = ELDService()
        eld_logs = eld_service.generate_logs(trip, stops)
        
        for log_data in eld_logs:
            ELDLog.objects.create(
                trip=trip,
                date=datetime.datetime.fromisoformat(log_data['date']),
                log_data=log_data['log_data']
            )
        
        return {
            "route_details": route_details,
            "stops": stops
        }
        
        
    def _determine_routes(self, routes_from_current_location_to_pickup_location, routes_from_pickup_location_to_dropoff_location):
        """Process route data from OSRM"""
        pickup_route = routes_from_current_location_to_pickup_location['routes'][0]
        dropoff_route = routes_from_pickup_location_to_dropoff_location['routes'][0]
        
        # in miles
        pickup_distance = pickup_route['distance'] / 1000
        dropoff_distance = dropoff_route['distance'] / 1000
        
        # in hours
        pickup_duration = pickup_route['duration'] / 3600 
        dropoff_duration = dropoff_route['duration'] / 3600
        
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
        
        """ print(f"Logging route data {route_data}") """
        
        return route_data
    
    
    def _determine_stops(self, trip, route_data):
        """Determines stops based on regulations (HOS)"""
        stops = []
        
        current_time = datetime.datetime.now()
        
        total_available_drive_time = 70.0
        daily_drive_limit = total_available_drive_time / 8 
        remaining_drive_time = daily_drive_limit - trip.current_cycle_hours
        remaining_duty_time = 14.0 - trip.current_cycle_hours
        
        stops.append({
            "location": trip.current_location,
            "arrival_time": current_time,
            "departure_time": current_time,
            "stop_type": StopType.START.value,
        })
        
        # Pickup phase
        pickup_drive_time = route_data["pickup_duration"]
        
        print(f"Pickup phase")
        print(f"Remaining drive time => {str(remaining_drive_time)}")
        print(f"Remaining duty time => {str(remaining_duty_time)}")
        print(f"Pickup drive time => {str(pickup_drive_time)}")
    
        if pickup_drive_time > remaining_drive_time:
            rest_stop = self._get_rest_stop(current_time, remaining_drive_time)
            stops.append(rest_stop["rest_stop"])
            current_time = rest_stop["current_time"]
            remaining_drive_time = daily_drive_limit
            remaining_duty_time = 14.0
        
        current_time += datetime.timedelta(hours=pickup_drive_time)
        remaining_drive_time -= pickup_drive_time
        remaining_duty_time -= pickup_drive_time
        
        stops.append({
            "location": trip.pickup_location,
            "arrival_time": current_time,
            "departure_time": current_time + datetime.timedelta(hours=self.add_time_for_pickup),
            "stop_type": StopType.PICKUP.value
        })
        
        current_time += datetime.timedelta(hours=self.add_time_for_pickup)
        remaining_duty_time -= self.add_time_for_pickup
        
        
        # Dropoff phase
        dropoff_drive_time = route_data["dropoff_duration"]
        
        print(f"Dropoff phase")
        print(f"Remaining drive time => {str(remaining_drive_time)}")
        print(f"Remaining duty time => {str(remaining_duty_time)}")
        print(f"Dropoff drive time => {str(dropoff_drive_time)}")
        
        total_distance = route_data["total_distance"]
        fuel_stops_needed = int(total_distance / 1000)
        
        print(f"Total distance => {str(total_distance)}")
        print(f"Fuel stops needed => {str(fuel_stops_needed)}")
        
        if fuel_stops_needed > 0:
            distance_between_stops = total_distance / (fuel_stops_needed + 1)
            total_trip_drive_time = (pickup_drive_time + dropoff_drive_time)
            time_between_stops = total_trip_drive_time / (fuel_stops_needed + 1)
            
            print(f"Total tripd drive time => {str(distance_between_stops)}")
            print(f"Time between stops => {str(time_between_stops)}")
            

            for i in range(fuel_stops_needed):
                if time_between_stops > remaining_drive_time:
                    rest_stop = self._get_rest_stop(current_time, remaining_drive_time, rest_location=f"Resting Location {i+1}")
                    stops.append(rest_stop["rest_stop"])
                    current_time = rest_stop["current_time"]
                    remaining_drive_time = daily_drive_limit
                    remaining_duty_time = 14.0

                fuel_location = f"Fuel Stop {i+1}"
                current_time += datetime.timedelta(hours=time_between_stops)
                remaining_drive_time -= time_between_stops
                remaining_duty_time -= time_between_stops

                stops.append({
                    "location": fuel_location,
                    "arrival_time": current_time,
                    "departure_time": current_time + datetime.timedelta(hours=self.add_time_for_fuel_stop),
                    "stop_type": StopType.FUEL.value
                })
                current_time += datetime.timedelta(hours=self.add_time_for_fuel_stop)
                remaining_duty_time -= self.add_time_for_fuel_stop

       
       
        remaining_drive_to_dropoff = dropoff_drive_time - (fuel_stops_needed * time_between_stops)
        if remaining_drive_to_dropoff > remaining_drive_time:
            rest_stop = self._get_rest_stop(current_time, remaining_drive_time, rest_location=f"Final Resting Location")
            stops.append(rest_stop["rest_stop"])
            current_time = rest_stop["current_time"]
            remaining_drive_time = total_available_drive_time
            remaining_duty_time = 14.0

        current_time += datetime.timedelta(hours=remaining_drive_to_dropoff)
        
        stops.append({
            "location": trip.dropoff_location,
            "arrival_time": current_time,
            "departure_time": current_time + datetime.timedelta(hours=self.add_time_for_dropoff),
            "stop_type": StopType.DROPOFF.value
        })

        return stops
    
    
    def _get_rest_stop(self, current_time, remaining_drive_time, rest_duration=10, rest_location="Resting Location"):
        print("Interpreting rest stop...")
        rest_duration = self.add_time_for_rest_stop
        rest_stop =  {
            "location": rest_location,
            "arrival_time": current_time + datetime.timedelta(hours=remaining_drive_time),
            "departure_time": current_time + datetime.timedelta(hours=remaining_drive_time + rest_duration),
            "stop_type": StopType.REST.value
        }
        current_time += datetime.timedelta(hours=remaining_drive_time + rest_duration)
        return {"current_time":current_time,"rest_stop":rest_stop}
