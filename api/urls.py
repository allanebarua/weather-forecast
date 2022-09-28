"""API URL Configurations."""
from rest_framework.urls import path
from api.views import get_aggregated_weather_forecast

# Function-Based Views
urlpatterns = [
    path('locations/<str:city>/', get_aggregated_weather_forecast, name='list-weather')
]
