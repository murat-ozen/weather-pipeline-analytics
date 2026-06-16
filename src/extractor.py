import logging
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Predefined locations for the pipeline
LOCATIONS = {
    "Istanbul": {"lat": 41.0082, "lon": 28.9784},
    "London": {"lat": 51.5074, "lon": -0.1278},
    "New York": {"lat": 40.7128, "lon": -74.0060},
    "Tokyo": {"lat": 35.6762, "lon": 139.6503}
}

class WeatherExtractor:
    """Handles data extraction from Open-Meteo API."""
    
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
    def __init__(self, locations: Dict[str, Dict[str, float]] = LOCATIONS):
        self.locations = locations

    def fetch_weather_data(self, city: str, lat: float, lon: float, past_days: int = 30) -> Dict[str, Any]:
        """Fetches daily historical and forecast weather data for a single city."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code",
            "timezone": "auto",
            "past_days": past_days,
            "forecast_days": 3 # 3 days forecast to show forward-looking data as well
        }
        
        logger.info(f"Extracting weather data for {city} (Lat: {lat}, Lon: {lon}) from Open-Meteo...")
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            data["city_name"] = city # Inject city name for identification downstream
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data for {city}: {e}")
            raise

    def extract_all(self, past_days: int = 30) -> List[Dict[str, Any]]:
        """Extracts data for all configured locations."""
        raw_datasets = []
        for city, coords in self.locations.items():
            try:
                raw_data = self.fetch_weather_data(city, coords["lat"], coords["lon"], past_days)
                raw_datasets.append(raw_data)
            except Exception as e:
                logger.warning(f"Skipping {city} due to extraction failure: {e}")
        return raw_datasets
