import logging
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# WMO Weather interpretation codes (https://open-meteo.com/en/docs)
WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
}

class WeatherTransformer:
    """Transforms raw API JSON data into clean Pandas DataFrames with engineered features."""

    def transform_single(self, raw_data: Dict[str, Any]) -> pd.DataFrame:
        """Transforms raw JSON data for a single city into a structured DataFrame."""
        city = raw_data["city_name"]
        daily_data = raw_data.get("daily", {})
        
        if not daily_data:
            logger.warning(f"No daily data found for {city}")
            return pd.DataFrame()
        
        # Create initial DataFrame from lists
        df = pd.DataFrame({
            "date": daily_data.get("time", []),
            "temp_max": daily_data.get("temperature_2m_max", []),
            "temp_min": daily_data.get("temperature_2m_min", []),
            "precipitation": daily_data.get("precipitation_sum", []),
            "wind_speed_max": daily_data.get("wind_speed_10m_max", []),
            "weather_code": daily_data.get("weather_code", [])
        })
        
        # Inject metadata
        df["city"] = city
        df["latitude"] = raw_data.get("latitude")
        df["longitude"] = raw_data.get("longitude")
        
        # --- Data Cleaning ---
        # Convert date column to datetime
        df["date"] = pd.to_datetime(df["date"])
        
        # Handle potential missing/null values
        df = df.dropna(subset=["date"])
        df["temp_max"] = df["temp_max"].ffill().bfill()
        df["temp_min"] = df["temp_min"].ffill().bfill()
        df["precipitation"] = df["precipitation"].fillna(0.0)
        df["wind_speed_max"] = df["wind_speed_max"].fillna(0.0)
        df["weather_code"] = df["weather_code"].fillna(-1).astype(int)
        
        # --- Feature Engineering ---
        # 1. Calculate Average Temperature and Temperature Range
        df["temp_mean"] = (df["temp_max"] + df["temp_min"]) / 2
        df["temp_range"] = df["temp_max"] - df["temp_min"]
        
        # 2. Flag rainy days (boolean)
        df["is_rainy"] = df["precipitation"] > 0
        
        # 3. Map weather codes to human-readable descriptions
        df["weather_desc"] = df["weather_code"].map(lambda x: WMO_WEATHER_CODES.get(x, "Unknown"))
        
        # 4. Create an extreme weather alert flag (e.g. temperature > 35 or < 0, or heavy wind/precipitation)
        df["is_extreme"] = (
            (df["temp_max"] > 35) | 
            (df["temp_min"] < 0) | 
            (df["wind_speed_max"] > 40) | 
            (df["precipitation"] > 25)
        )
        
        # Rearrange columns for clean structure
        column_order = [
            "city", "date", "latitude", "longitude", 
            "temp_max", "temp_min", "temp_mean", "temp_range", 
            "precipitation", "is_rainy", "wind_speed_max", 
            "weather_code", "weather_desc", "is_extreme"
        ]
        return df[column_order]

    def transform_all(self, raw_datasets: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transforms and aggregates datasets from all cities into a single master DataFrame."""
        logger.info("Transforming raw data and performing feature engineering using Pandas...")
        
        dfs = []
        for raw_data in raw_datasets:
            city_df = self.transform_single(raw_data)
            if not city_df.empty:
                dfs.append(city_df)
                
        if not dfs:
            logger.error("No valid data transformed.")
            return pd.DataFrame()
            
        # Combine all dataframes
        master_df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Transformation complete. Total rows: {len(master_df)}")
        return master_df
