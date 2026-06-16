import logging
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

logger = logging.getLogger(__name__)

# Use a clean, modern aesthetic style for plotting
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 13,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.titlesize": 15
})

class WeatherAnalytics:
    """Performs SQL-based analytics and generates beautiful visualizations for the weather database."""

    def __init__(self, db_path: str = "data/weather_data.db", export_dir: str = "exports"):
        self.db_path = db_path
        self.export_dir = export_dir
        Path(self.export_dir).mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def run_analytics(self):
        """Runs the complete SQL analytics query set and generates the visual charts."""
        logger.info("Starting SQL data analytics and visualization generation...")
        
        # Connect and load data into pandas for plotting
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query("SELECT * FROM daily_weather ORDER BY date ASC", conn)
                
            if df.empty:
                logger.error("No data found in database to analyze.")
                return
                
            df["date"] = pd.to_datetime(df["date"])
            
            # Generate and save the three core visualization charts
            self._plot_temperature_trends(df)
            self._plot_precipitation_comparison(df)
            self._plot_climate_distributions(df)
            
            # Print a summary of SQL insights to the console
            self._print_sql_insights()
            
            logger.info(f"Visualizations successfully generated and saved to: {self.export_dir}/")
        except Exception as e:
            logger.error(f"Error during analytics execution: {e}")
            raise

    def _plot_temperature_trends(self, df: pd.DataFrame):
        """Generates a line plot showing temperature trends for all cities over time."""
        plt.figure(figsize=(12, 6))
        
        # Premium color palette
        palette = sns.color_palette("husl", n_colors=len(df["city"].unique()))
        
        sns.lineplot(
            data=df, 
            x="date", 
            y="temp_mean", 
            hue="city", 
            palette=palette,
            linewidth=2.5,
            marker="o",
            markersize=4
        )
        
        plt.title("Daily Average Temperature Trends (Past 30 Days + 3 Days Forecast)", weight="bold", pad=15)
        plt.xlabel("Date", labelpad=10)
        plt.ylabel("Temperature (°C)", labelpad=10)
        plt.legend(title="City", frameon=True, shadow=True, facecolor="white")
        plt.tight_layout()
        
        chart_path = Path(self.export_dir) / "temperature_trends.png"
        plt.savefig(chart_path, dpi=300)
        plt.close()
        logger.info(f"Saved temperature trends chart to {chart_path}")

    def _plot_precipitation_comparison(self, df: pd.DataFrame):
        """Generates a bar plot comparing the total accumulated precipitation by city."""
        # Query total precipitation via SQL to keep it query-focused
        query = """
        SELECT city, SUM(precipitation) as total_precipitation
        FROM daily_weather
        GROUP BY city
        ORDER BY total_precipitation DESC;
        """
        with self._get_connection() as conn:
            precip_df = pd.read_sql_query(query, conn)

        plt.figure(figsize=(8, 5))
        
        # Deep blue-teal custom gradient palette
        colors = sns.color_palette("YlGnBu_r", n_colors=len(precip_df))
        
        barplot = sns.barplot(
            data=precip_df, 
            x="city", 
            y="total_precipitation", 
            palette=colors,
            hue="city",
            legend=False,
            edgecolor="black",
            linewidth=0.8
        )
        
        # Add labels on top of the bars
        for container in barplot.containers:
            barplot.bar_label(container, fmt="%.1f mm", padding=3, weight="semibold")

        plt.title("Accumulated Rainfall Comparison by City (Past 30 Days)", weight="bold", pad=15)
        plt.xlabel("City", labelpad=10)
        plt.ylabel("Total Precipitation (mm)", labelpad=10)
        plt.tight_layout()
        
        chart_path = Path(self.export_dir) / "precipitation_comparison.png"
        plt.savefig(chart_path, dpi=300)
        plt.close()
        logger.info(f"Saved precipitation comparison chart to {chart_path}")

    def _plot_climate_distributions(self, df: pd.DataFrame):
        """Generates a violin plot to compare the temperature ranges and spreads across cities."""
        plt.figure(figsize=(9, 6))
        
        sns.violinplot(
            data=df, 
            x="city", 
            y="temp_mean", 
            palette="Set2",
            hue="city",
            legend=False,
            inner="quartile",
            linewidth=1.5
        )
        
        plt.title("Temperature Distribution & Quartiles Comparison", weight="bold", pad=15)
        plt.xlabel("City", labelpad=10)
        plt.ylabel("Average Daily Temperature (°C)", labelpad=10)
        plt.tight_layout()
        
        chart_path = Path(self.export_dir) / "temperature_distribution.png"
        plt.savefig(chart_path, dpi=300)
        plt.close()
        logger.info(f"Saved temperature distribution chart to {chart_path}")

    def _print_sql_insights(self):
        """Runs custom SQL queries to extract key statistics to output to the console."""
        queries = {
            "Extreme Weather Events Counter": """
                SELECT city, COUNT(*) as extreme_days_count 
                FROM daily_weather 
                WHERE is_extreme = 1 
                GROUP BY city;
            """,
            "Hottest Days Recorded": """
                SELECT city, date, temp_max 
                FROM daily_weather 
                WHERE temp_max = (SELECT MAX(temp_max) FROM daily_weather);
            """,
            "Wettest Days Recorded": """
                SELECT city, date, precipitation, weather_desc
                FROM daily_weather 
                WHERE precipitation > 0
                ORDER BY precipitation DESC
                LIMIT 3;
            """
        }
        
        print("\n" + "="*50)
        print("           SQL DATABASE ANALYTICAL INSIGHTS           ")
        print("="*50)
        
        with self._get_connection() as conn:
            for title, query in queries.items():
                print(f"\n>>> {title}:")
                try:
                    df_res = pd.read_sql_query(query, conn)
                    if df_res.empty:
                        print("    No matching records found.")
                    else:
                        print(df_res.to_string(index=False, justify="left"))
                except sqlite3.Error as e:
                    print(f"    SQL Query failed: {e}")
        print("="*50 + "\n")
