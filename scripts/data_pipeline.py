import asyncio
import argparse
import pandas as pd
import os
import sys
from datetime import datetime

# Add the project root to the Python path to allow for absolute imports
# This is necessary so the script can find modules like 'core' when run from the command line.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.engine import TradingEngine
from utils.logger import logger

async def run_data_pipeline(exchange: str, pair: str, duration: int, interval: int):
    """
    Captures L2 order book snapshots and persists them to Parquet files.
    This script fulfills the requirements of Task 5.
    
    Args:
        exchange (str): The name of the exchange to pull data from.
        pair (str): The universal symbol of the pair.
        duration (int): The total time to run the pipeline in seconds.
        interval (int): The time to wait between captures in seconds.
    """
    engine = TradingEngine()
    connector = engine.connectors.get(exchange)

    if not connector:
        logger.error(f"Connector for '{exchange}' not found or not configured.")
        return

    logger.info(f"--- Starting Data Pipeline for {exchange.upper()} / {pair} ---")
    logger.info(f"Running for {duration} seconds, capturing data every {interval} seconds.")
    
    start_time = asyncio.get_event_loop().time()
    all_snapshots = []

    while (asyncio.get_event_loop().time() - start_time) < duration:
        loop_start_time = asyncio.get_event_loop().time()
        
        try:
            timestamp = datetime.utcnow()
            order_book = await connector.get_l2_order_book(pair)
            
            # Flatten the data for efficient storage in a DataFrame
            # Each row represents a single price level on the order book at a point in time.
            for price, quantity in order_book['bids']:
                all_snapshots.append({
                    'timestamp': timestamp,
                    'side': 'bid',
                    'price': price,
                    'quantity': quantity
                })
            for price, quantity in order_book['asks']:
                all_snapshots.append({
                    'timestamp': timestamp,
                    'side': 'ask',
                    'price': price,
                    'quantity': quantity
                })
            
            logger.info(f"[{timestamp.isoformat()}] Captured snapshot. Total records so far: {len(all_snapshots)}")

        except Exception as e:
            logger.error(f"[{datetime.utcnow().isoformat()}] Error capturing snapshot: {e}")

        # Wait for the next interval, accounting for the time the API call took
        elapsed = asyncio.get_event_loop().time() - loop_start_time
        await asyncio.sleep(max(0, interval - elapsed))

    if not all_snapshots:
        logger.warning("No data was collected. Exiting.")
        return

    # --- Persist Data to Parquet ---
    logger.info("--- Data Collection Finished. Persisting to disk... ---")
    df = pd.DataFrame(all_snapshots)
    
    # Create a partitioned path according to the requirements: /data/exchange=.../pair=.../date=...
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    exchange_pair_str = pair.replace('/', '-') # Use a filesystem-friendly separator
    output_dir = os.path.join('data', f'exchange={exchange}', f'pair={exchange_pair_str}', f'date={date_str}')
    os.makedirs(output_dir, exist_ok=True)
    
    # Use a timestamp for the filename to avoid overwriting files from the same day
    output_file = os.path.join(output_dir, f'{datetime.utcnow().strftime("%H%M%S")}.parquet')
    
    try:
        # Save the DataFrame to a Parquet file, which is efficient for large datasets
        df.to_parquet(output_file, engine='pyarrow', compression='snappy')
        logger.info(f"Successfully saved {len(df)} records to: {output_file}")
    except Exception as e:
        logger.error(f"Failed to save data to Parquet file: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a data persistence pipeline for L2 order books (Task 5).")
    parser.add_argument("--exchange", type=str, required=True, help="The exchange to use.")
    parser.add_argument("--pair", type=str, required=True, help="The universal pair symbol.")
    parser.add_argument("--duration", type=int, default=600, help="Total duration to run in seconds (default: 10 mins).")
    parser.add_argument("--interval", type=int, default=1, help="Interval between captures in seconds (default: 1s).")
    args = parser.parse_args()

    asyncio.run(run_data_pipeline(args.exchange, args.pair, args.duration, args.interval))
