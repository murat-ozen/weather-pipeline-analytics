import logging
import sqlite3
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

class WeatherLoader:
    """Manages SQLite database initialization and data ingestion (ETL - Load phase)."""

    def __init__(self, db_path: str = "data/weather_data.db"):
        self.db_path = db_path
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)

    def initialize_database(self):
        """Creates the weather data table and associated indexes if they do not exist."""
        ddl_query = """
        CREATE TABLE IF NOT EXISTS daily_weather (
            city TEXT NOT NULL,
            date TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            temp_max REAL,
            temp_min REAL,
            temp_mean REAL,
            temp_range REAL,
            precipitation REAL,
            is_rainy INTEGER,
            wind_speed_max REAL,
            weather_code INTEGER,
            weather_desc TEXT,
            is_extreme INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (city, date)
        );
        """
        
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_weather_city_date ON daily_weather(city, date);",
            "CREATE INDEX IF NOT EXISTS idx_weather_date ON daily_weather(date);"
        ]
        
        logger.info(f"Initializing SQLite database at {self.db_path}...")
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Create table
                cursor.execute(ddl_query)
                # Create indexes
                for query in index_queries:
                    cursor.execute(query)
                conn.commit()
            logger.info("Database initialized successfully with schemas and indexes.")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def load_data(self, df: pd.DataFrame):
        """Upserts (Insert or Replace) the Pandas DataFrame into the SQLite database."""
        if df.empty:
            logger.warning("Empty DataFrame provided. Skipping ingestion.")
            return

        insert_query = """
        INSERT OR REPLACE INTO daily_weather (
            city, date, latitude, longitude, 
            temp_max, temp_min, temp_mean, temp_range, 
            precipitation, is_rainy, wind_speed_max, 
            weather_code, weather_desc, is_extreme
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        
        logger.info(f"Ingesting {len(df)} rows into SQLite database...")
        
        # Prepare records for insertion (convert Timestamp to ISO string format)
        records = []
        for _, row in df.iterrows():
            records.append((
                row["city"],
                row["date"].strftime("%Y-%m-%d"),
                row["latitude"],
                row["longitude"],
                row["temp_max"],
                row["temp_min"],
                row["temp_mean"],
                row["temp_range"],
                row["precipitation"],
                1 if row["is_rainy"] else 0,
                row["wind_speed_max"],
                int(row["weather_code"]),
                row["weather_desc"],
                1 if row["is_extreme"] else 0
            ))
            
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(insert_query, records)
                conn.commit()
            logger.info(f"Database ingestion complete. Successfully loaded {len(df)} records.")
        except sqlite3.Error as e:
            logger.error(f"Failed to ingest data into SQLite: {e}")
            raise
            
    def get_summary_statistics(self) -> pd.DataFrame:
        """Helper method to query data back using SQL to verify load correctness."""
        query = """
        SELECT 
            city,
            COUNT(*) as record_count,
            MIN(date) as start_date,
            MAX(date) as end_date,
            ROUND(AVG(temp_mean), 2) as avg_temp,
            ROUND(MAX(temp_max), 2) as absolute_max_temp,
            ROUND(MIN(temp_min), 2) as absolute_min_temp,
            SUM(precipitation) as total_precipitation
        FROM daily_weather
        GROUP BY city;
        """
        try:
            with self._get_connection() as conn:
                return pd.read_sql_query(query, conn)
        except sqlite3.Error as e:
            logger.error(f"Error querying summary statistics: {e}")
            return pd.DataFrame()
