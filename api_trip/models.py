from django.db import models

class Trip(models.Model):
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_hours = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Trip from {self.current_location} to {self.dropoff_location}"

class RouteStop(models.Model):
    trip = models.ForeignKey(Trip, related_name='stops', on_delete=models.CASCADE)
    location = models.CharField(max_length=255)
    arrival_time = models.DateTimeField()
    departure_time = models.DateTimeField(null=True, blank=True)
    stop_type = models.CharField(max_length=50)  # 'rest', 'fuel', 'pickup', 'dropoff'
    
    def __str__(self):
        return f"{self.stop_type} at {self.location}"

class ELDLog(models.Model):
    trip = models.ForeignKey(Trip, related_name='eld_logs', on_delete=models.CASCADE)
    date = models.DateField()
    log_data = models.JSONField()  # Store log activities
    
    def __str__(self):
        return f"Log for {self.date}"
