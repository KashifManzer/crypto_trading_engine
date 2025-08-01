import asyncio
from typing import Dict, List, Optional

from config import API_KEYS
from connectors.base_connector import ExchangeConnector
from connectors.binance_connector import BinanceConnector
from connectors.kucoin_connector import KucoinConnector
from connectors.bybit_connector import BybitConnector
from connectors.okx_connector import OkxConnector
from connectors.bitmart_connector import BitmartConnector
from utils.logger import logger

class TradingEngine:
    """
    The core engine that orchestrates operations across multiple exchanges.
    It loads all configured connectors and provides high-level functions
    to interact with them in a unified way.
    """
    def __init__(self):
        """Initializes the engine by loading all available connectors."""
        self.connectors: Dict[str, ExchangeConnector] = self._load_connectors()

    def _load_connectors(self) -> Dict[str, ExchangeConnector]:
        """
        Loads all exchange connectors that have their API keys configured
        in the environment variables.
        """
        connectors = {}
        # Map exchange names to their corresponding connector classes
        connector_classes = {
            "binance": BinanceConnector,
            "kucoin": KucoinConnector,
            "bybit": BybitConnector,
            "okx": OkxConnector,
            "bitmart": BitmartConnector,
        }

        loaded_count = 0
        for name, creds in API_KEYS.items():
            # Check if both api_key and api_secret are present
            if creds.get("api_key") and creds.get("api_secret"):
                try:
                    connector_class = connector_classes.get(name)
                    if connector_class:
                        # Instantiate the connector with its credentials
                        connectors[name] = connector_class(**creds)
                        logger.info(f"Successfully loaded connector: {name}")
                        loaded_count += 1
                    else:
                        logger.warning(f"No connector class found for {name}")
                except Exception as e:
                    logger.error(f"Failed to load connector {name}: {str(e)}")
            else:
                logger.info(f"Skipping {name}: API keys not configured")

        if loaded_count == 0:
            logger.warning("No connectors were loaded! Please check your .env file and ensure at least one exchange has API keys configured.")
        
        return connectors

    async def find_best_cross_exchange_bid_ask(self, pair: str) -> Dict[str, Optional[Dict]]:
        """
        Finds the best (highest) bid and best (lowest) ask for a given pair
        by concurrently querying all loaded exchanges.
        
        Args:
            pair (str): The universal symbol for the trading pair (e.g., 'BTC/USDT').
            
        Returns:
            A dictionary containing the best bid and ask found, including the
            exchange name and price for each.
        """
        if not self.connectors:
            logger.warning("No connectors available for cross-exchange bid/ask search")
            return {'best_bid': None, 'best_ask': None, 'error': 'No connectors available'}
        
        logger.info(f"Finding best cross-exchange bid/ask for {pair}")
        tasks = [conn.get_best_bid_ask(pair) for conn in self.connectors.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        best_bid = None
        best_ask = None
        errors = []
        
        for i, result in enumerate(results):
            exchange_name = list(self.connectors.keys())[i]
            if isinstance(result, Exception):
                error_msg = f"Error fetching data from {exchange_name}: {result}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue

            # Find the highest bid
            if best_bid is None or result['bid'] > best_bid['price']:
                best_bid = {'exchange': exchange_name, 'price': result['bid']}
            
            # Find the lowest ask
            if best_ask is None or result['ask'] < best_ask['price']:
                best_ask = {'exchange': exchange_name, 'price': result['ask']}
        
        result = {'best_bid': best_bid, 'best_ask': best_ask}
        if errors:
            result['errors'] = errors
            logger.warning(f"Found {len(errors)} errors during cross-exchange search")
        
        if best_bid and best_ask:
            logger.info(f"Best cross-exchange prices for {pair}: bid={best_bid['price']} on {best_bid['exchange']}, ask={best_ask['price']} on {best_ask['exchange']}")
        
        return result

# Example Usage Block
async def main():
    """Main function to demonstrate the TradingEngine's capabilities."""
    engine = TradingEngine()
    if not engine.connectors:
        logger.warning("No connectors were loaded. Please check your .env file and API keys.")
        return

    logger.info("Finding best cross-exchange bid/ask for BTC/USDT...")
    best_prices = await engine.find_best_cross_exchange_bid_ask('BTC/USDT')
    
    if best_prices.get('error'):
        logger.error(f"Error: {best_prices['error']}")
        return
    
    if best_prices['best_bid'] and best_prices['best_ask']:
        logger.info(f"Best Bid: {best_prices['best_bid']['price']} on {best_prices['best_bid']['exchange']}")
        logger.info(f"Best Ask: {best_prices['best_ask']['price']} on {best_prices['best_ask']['exchange']}")
        
        # Calculate spread
        spread = best_prices['best_ask']['price'] - best_prices['best_bid']['price']
        spread_percent = (spread / best_prices['best_bid']['price']) * 100
        logger.info(f"Spread: {spread:.2f} ({spread_percent:.4f}%)")
    else:
        logger.warning("Could not retrieve prices from any exchange.")
    
    if best_prices.get('errors'):
        logger.warning(f"Errors encountered: {len(best_prices['errors'])}")

if __name__ == '__main__':
    # This allows the script to be run directly to test its functionality.
    asyncio.run(main())
