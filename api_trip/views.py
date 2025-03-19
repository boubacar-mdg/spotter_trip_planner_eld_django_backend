from django.shortcuts import render
from rest_framework import viewsets, status
from .models import Trip, RouteStop
from .serializers import TripSerializer
from rest_framework.decorators import action
from .services.route_service import RouteService
from rest_framework.response import Response

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    
    @action(detail=True, methods=['post'])
    def determine_route_stops(self, request, pk=None):
        """Determine route with stops"""
        trip = self.get_object()
        
        print(f"Current trip: {str(trip)}")
        
        route_service = RouteService()
        route_result = route_service.determine_routes_and_stops(trip)
        
        serializer = self.get_serializer(trip)
        return Response(serializer.data)
    
    