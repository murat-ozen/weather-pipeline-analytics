import argparse
import logging
import sys
from src.extractor import WeatherExtractor
from src.transformer import WeatherTransformer
from src.loader import WeatherLoader
from src.analytics import WeatherAnalytics

# Setup clean log formatting
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("weather_pipeline")

def run_etl_pipeline(past_days: int = 30):
    """Executes the full Extract, Transform, and Load (ETL) process."""
    logger.info("================ STARTING WEATHER ETL PIPELINE ================")
    
    # 1. Extraction Phase
    extractor = WeatherExtractor()
    raw_data = extractor.extract_all(past_days=past_days)
    
    if not raw_data:
        logger.error("No data extracted. Aborting ETL pipeline.")
        return None
        
    # 2. Transformation Phase
    transformer = WeatherTransformer()
    clean_df = transformer.transform_all(raw_data)
    
    if clean_df.empty:
        logger.error("Dataframe is empty after transformation. Aborting ETL pipeline.")
        return None
        
    # 3. Load Phase
    loader = WeatherLoader()
    loader.initialize_database()
    loader.load_data(clean_df)
    
    # Verify load correctness by fetching statistics
    stats_df = loader.get_summary_statistics()
    logger.info("\n>>> Ingested Database Overview (via SQL SELECT GROUP BY):\n" + stats_df.to_string(index=False))
    
    logger.info("================ ETL PIPELINE COMPLETED SUCCESSFULLY ================")
    return clean_df

def run_analytics_pipeline():
    """Runs database queries and creates visual charts."""
    logger.info("================ STARTING WEATHER ANALYTICS & VISUALIZATION ================")
    analytics = WeatherAnalytics()
    analytics.run_analytics()
    logger.info("================ ANALYTICS & VISUALIZATION COMPLETED ================")

def main():
    parser = argparse.ArgumentParser(
        description="Weather Data Pipeline & Analytics (End-to-End Data Engineer/Analyst Portfolio Project)"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        default=30, 
        help="Number of historical days to fetch from the API (default: 30)"
    )
    parser.add_argument(
        "--etl-only", 
        action="store_true", 
        help="Run only the ETL extraction, transformation, and ingestion phases"
    )
    parser.add_argument(
        "--analytics-only", 
        action="store_true", 
        help="Run only the SQL analytics queries and visualization generation"
    )
    
    args = parser.parse_args()
    
    try:
        if args.analytics_only:
            run_analytics_pipeline()
        elif args.etl_only:
            run_etl_pipeline(past_days=args.days)
        else:
            # Run the full end-to-end pipeline by default
            run_etl_pipeline(past_days=args.days)
            run_analytics_pipeline()
            
    except Exception as e:
        logger.critical(f"Pipeline failed catastrophically: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
