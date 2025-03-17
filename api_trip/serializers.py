from rest_framework import serializers
from .models import Trip, RouteStop, ELDLog

class RouteStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteStop
        fields = ['id', 'location', 'arrival_time', 'departure_time', 'stop_type']

class ELDLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ELDLog
        fields = ['id', 'date', 'log_data']

class TripSerializer(serializers.ModelSerializer):
    stops = RouteStopSerializer(many=True, read_only=True)
    eld_logs = ELDLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Trip
        fields = ['id', 'current_location', 'pickup_location', 'dropoff_location', 
                  'current_cycle_hours', 'created_at', 'stops', 'eld_logs']