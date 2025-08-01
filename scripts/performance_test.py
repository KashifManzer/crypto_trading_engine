import asyncio
import time
import argparse
import random
import sys
import os

# Add the project root to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.engine import TradingEngine
from utils.logger import logger

async def run_performance_test(exchange: str, pair: str, count: int):
    """
    Runs a performance test by placing and then immediately canceling orders.
    This script fulfills the requirements of Task 2.

    Args:
        exchange (str): The name of the exchange to test.
        pair (str): The universal symbol of the pair to trade.
        count (int): The number of orders to place and cancel.
    """
    engine = TradingEngine()
    connector = engine.connectors.get(exchange)

    if not connector:
        logger.error(f"Connector for '{exchange}' not found or not configured.")
        return

    logger.info(f"--- Starting Performance Test on {exchange.upper()} for {pair} ---")
    logger.info(f"Attempting to place and cancel {count} orders...")
    logger.warning("WARNING: This test will attempt to execute REAL orders. Use with caution.")

    placements = {'success': 0, 'failed': 0, 'latencies': []}
    cancellations = {'success': 0, 'failed': 0, 'latencies': []}

    for i in range(count):
        # Use a very small quantity for the test to minimize cost
        quantity = 0.0001
        order_type = random.choice(['MARKET', 'LIMIT'])
        
        # For LIMIT orders, place it slightly away from the market to avoid immediate fills
        price = None
        if order_type == 'LIMIT':
            try:
                ticker = await connector.get_best_bid_ask(pair)
                # Place a buy limit 5% below the current bid to ensure it's not filled
                price = ticker['bid'] * 0.95 
            except Exception as e:
                logger.error(f"Could not fetch ticker to set limit price, skipping iteration: {e}")
                continue

        # --- Place Order ---
        order_id = None
        start_time = time.monotonic()
        try:
            result = await connector.place_order(pair, 'buy', quantity, order_type, price)
            latency = time.monotonic() - start_time
            placements['latencies'].append(latency)
            placements['success'] += 1
            order_id = result.get('order_id')
            logger.info(f"[{i+1}/{count}] Placed {order_type} order successfully. ID: {order_id}. Latency: {latency:.4f}s")
        except Exception as e:
            latency = time.monotonic() - start_time
            placements['failed'] += 1
            logger.error(f"[{i+1}/{count}] Failed to place order. Latency: {latency:.4f}s. Error: {e}")

        # Give the exchange a moment to process the order
        await asyncio.sleep(0.5)

        # --- Cancel Order ---
        if order_id:
            start_time = time.monotonic()
            try:
                await connector.cancel_order(str(order_id), pair)
                latency = time.monotonic() - start_time
                cancellations['latencies'].append(latency)
                cancellations['success'] += 1
                logger.info(f"[{i+1}/{count}] Canceled order successfully. ID: {order_id}. Latency: {latency:.4f}s")
            except Exception as e:
                latency = time.monotonic() - start_time
                cancellations['failed'] += 1
                logger.error(f"[{i+1}/{count}] Failed to cancel order. ID: {order_id}. Latency: {latency:.4f}s. Error: {e}")
        
        # Be respectful of API rate limits
        await asyncio.sleep(0.5) 

    # --- Print Summary ---
    logger.info("--- Performance Test Summary ---")
    avg_place_latency = sum(placements['latencies']) / len(placements['latencies']) if placements['latencies'] else 0
    avg_cancel_latency = sum(cancellations['latencies']) / len(cancellations['latencies']) if cancellations['latencies'] else 0
    
    logger.info("Order Placement:")
    logger.info(f"  Success Rate: {placements['success'] / count * 100:.2f}% ({placements['success']}/{count})")
    logger.info(f"  Average Latency: {avg_place_latency:.4f}s")

    logger.info("Order Cancellation:")
    cancel_count = placements['success']
    if cancel_count > 0:
        logger.info(f"  Success Rate: {cancellations['success'] / cancel_count * 100:.2f}% ({cancellations['success']}/{cancel_count})")
        logger.info(f"  Average Latency: {avg_cancel_latency:.4f}s")
    else:
        logger.info("  No orders were successfully placed to attempt cancellation.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a trading performance test (Task 2).")
    parser.add_argument("--exchange", type=str, required=True, help="The exchange to test (e.g., 'binance').")
    parser.add_argument("--pair", type=str, required=True, help="The universal pair symbol (e.g., 'BTC/USDT').")
    parser.add_argument("--count", type=int, default=10, help="The number of orders to test.")
    args = parser.parse_args()

    asyncio.run(run_performance_test(args.exchange, args.pair, args.count))
