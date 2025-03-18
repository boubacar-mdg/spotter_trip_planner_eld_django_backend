import datetime


class ELDService:
    def __init__(self):
        
        self.status_map = {
            "start": "ON",    
            "rest": "SB",     
            "fuel": "ON",     
            "pickup": "ON",   
            "dropoff": "ON",  
            "off": "OFF"      
        }
        self.driving_status = "D" 
        
        self.limits = {
            "driving_daily": 8.75,   
            "on_duty_daily": 14, 
        }
    
    def generate_logs(self, trip, route_stops):
        """Generate ELD logs based on trip and stops"""
        if not trip or not route_stops:
            raise ValueError("Trip and route stops are required")
        
        days = {}
        current_odometer = 0 
        
        for i, stop in enumerate(route_stops):
            arrival_time = stop["arrival_time"]
            departure_time = stop["departure_time"]
            date_key = arrival_time.date().isoformat()
            
            if date_key not in days:
                days[date_key] = []
            
            
            estimated_odometer = current_odometer + (i * 1) 
            
            days[date_key].append({
                "time": arrival_time,
                "status": self.status_map[stop["stop_type"]],
                "location": stop["location"],
                "odometer": estimated_odometer,
                "remarks": f"Arrived at {stop['stop_type']} stop"
            })
            
            if i < len(route_stops) - 1:
                next_stop = route_stops[i + 1]
                
            
                driving_distance = 50 
                
                driving_time = (next_stop["arrival_time"] - departure_time).total_seconds() / 3600
                

                if departure_time.date() != next_stop["arrival_time"].date():
                    midnight = datetime.datetime.combine(departure_time.date(), 
                                                         datetime.time(23, 59, 59))
                    total_driving_seconds = (next_stop["arrival_time"] - departure_time).total_seconds()
                    seconds_before_midnight = (midnight - departure_time).total_seconds()
                    proportion_before_midnight = seconds_before_midnight / total_driving_seconds
                    
                    midnight_odometer = estimated_odometer + (driving_distance * proportion_before_midnight)
                    
                    days[date_key].append({
                        "time": departure_time,
                        "status": self.driving_status,
                        "location": f"Going from {stop['location']} to {next_stop['location']}",
                        "odometer": estimated_odometer,
                        "remarks": f"Driving to {next_stop['location']}"
                    })
                    
                    days[date_key].append({
                        "time": midnight,
                        "status": self.driving_status,
                        "location": f"Going from {stop['location']} to {next_stop['location']}",
                        "odometer": midnight_odometer,
                        "remarks": "End of day"
                    })
                    
                    next_day_key = next_stop["arrival_time"].date().isoformat()
                    if next_day_key not in days:
                        days[next_day_key] = []
                    
                    start_of_day = datetime.datetime.combine(next_stop["arrival_time"].date(), 
                                                            datetime.time(0, 0, 0))
                    
                    days[next_day_key].append({
                        "time": start_of_day,
                        "status": self.driving_status,
                        "location": f"Going from {stop['location']} to {next_stop['location']}",
                        "odometer": midnight_odometer,
                        "remarks": "Start of day"
                    })
                else:
                    days[date_key].append({
                        "time": departure_time,
                        "status": self.driving_status,
                        "location": f"Going from {stop['location']} to {next_stop['location']}",
                        "odometer": estimated_odometer,
                        "remarks": f"Driving to {next_stop['location']}"
                    })
                
                current_odometer = estimated_odometer + driving_distance
        
        eld_logs = []
        for date_str, events in days.items():
            events.sort(key=lambda x: x["time"])
            
            hours_summary = self._calculate_hours_summary(events)
            hos_violations = self._check_hos_violations(hours_summary)
            
            miles_driven = self._calculate_miles_driven(events)
            
            log_data = {
                "carrier": "Carrier #1", 
                "driver_name": "Bouabacar Demba Mandiang",  
                "driver_id": "12345",          
                "truck_number": "T-001",     
                "trailer_numbers": "TR-001", 
                "shipping_doc": "DOC-" + str(trip.id),
                "events": [
                    {
                        "time": event["time"].strftime("%H:%M"),
                        "status": event["status"],
                        "location": event["location"],
                        "odometer": round(event["odometer"], 1),
                        "remarks": event.get("remarks", "")
                    } for event in events
                ],
                "hours_summary": hours_summary,
                "hos_violations": hos_violations,
                "miles_driven": miles_driven,
                "certification": False
            }
            
            log = {
                "date": date_str,
                "log_data": log_data
            }
            eld_logs.append(log)
        
        return eld_logs
    
    def certify_log(self, log_id, driver_id):
        """Certify a log as accurate by the driver"""
        return {
            "log_id": log_id,
            "certified": True,
            "certification_time": datetime.datetime.now(),
            "driver_id": driver_id
        }
    
    def _calculate_hours_summary(self, events):
        """Calculate hours summary based on events"""
        
        summary = {
            "driving": 0,
            "on_duty_not_driving": 0,
            "sleeper_berth": 0,
            "off_duty": 0,
            "total_on_duty": 0,
            "total": 0
        }
        
        
        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]
            
            duration = (next_event["time"] - current["time"]).total_seconds() / 3600
            
            if current["status"] == "D":
                summary["driving"] += duration
            elif current["status"] == "ON":
                summary["on_duty_not_driving"] += duration
            elif current["status"] == "SB":
                summary["sleeper_berth"] += duration
            elif current["status"] == "OFF":
                summary["off_duty"] += duration
        
        
        summary["total_on_duty"] = summary["driving"] + summary["on_duty_not_driving"]
        summary["total"] = (
            summary["driving"] + 
            summary["on_duty_not_driving"] + 
            summary["sleeper_berth"] + 
            summary["off_duty"]
        )
        
        
        for key in summary:
            summary[key] = round(summary[key], 2)
        
        return summary
    
    def _check_hos_violations(self, hours_summary):
        """Check for Hours of Service violations"""
        violations = []
        
        if hours_summary["driving"] > self.limits["driving_daily"]:
            violations.append({
                "type": "11-hour driving limit exceeded",
                "limit": self.limits["driving_daily"],
                "actual": hours_summary["driving"]
            })
        
        if hours_summary["total_on_duty"] > self.limits["on_duty_daily"]:
            violations.append({
                "type": "14-hour on-duty limit exceeded",
                "limit": self.limits["on_duty_daily"],
                "actual": hours_summary["total_on_duty"]
            })
        
        return violations
    
    def _calculate_miles_driven(self, events):
        """Calculate total miles driven in a day"""
        if not events:
            return 0
        
        driving_events = [e for e in events if e["status"] == "D"]
        if not driving_events:
            return 0
        
        min_odometer = min(driving_events, key=lambda x: x["odometer"])["odometer"]
        max_odometer = max(driving_events, key=lambda x: x["odometer"])["odometer"]
        
        return round(max_odometer - min_odometer, 1)