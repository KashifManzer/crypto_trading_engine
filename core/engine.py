import asyncio
from typing import Dict, List, Optional

from config import API_KEYS
from connectors.base_connector import ExchangeConnector
from connectors.binance_connector import BinanceConnector
from connectors.kucoin_connector import KucoinConnector
from connectors.bybit_connector import BybitConnector
from connectors.okx_connector import OkxConnector
from connectors.bitmart_connector import BitmartConnector

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
                        print(f"Successfully loaded connector: {name}")
                        loaded_count += 1
                    else:
                        print(f"Warning: No connector class found for {name}")
                except Exception as e:
                    print(f"Failed to load connector {name}: {e}")
            else:
                print(f"Skipping {name}: API keys not configured")

        if loaded_count == 0:
            print("\n⚠️  WARNING: No connectors were loaded!")
            print("Please check your .env file and ensure at least one exchange has API keys configured.")
            print("You can copy env.example to .env and fill in your API keys.")
        
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
            return {'best_bid': None, 'best_ask': None, 'error': 'No connectors available'}
        
        tasks = [conn.get_best_bid_ask(pair) for conn in self.connectors.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        best_bid = None
        best_ask = None
        errors = []
        
        for i, result in enumerate(results):
            exchange_name = list(self.connectors.keys())[i]
            if isinstance(result, Exception):
                error_msg = f"Error fetching data from {exchange_name}: {result}"
                print(error_msg)
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
        return result

# Example Usage Block
async def main():
    """Main function to demonstrate the TradingEngine's capabilities."""
    engine = TradingEngine()
    if not engine.connectors:
        print("\nNo connectors were loaded. Please check your .env file and API keys.")
        print("You can copy env.example to .env and fill in your API keys.")
        return

    print("\nFinding best cross-exchange bid/ask for BTC/USDT...")
    best_prices = await engine.find_best_cross_exchange_bid_ask('BTC/USDT')
    
    if best_prices.get('error'):
        print(f"Error: {best_prices['error']}")
        return
    
    if best_prices['best_bid'] and best_prices['best_ask']:
        print(f"  -> Best Bid: {best_prices['best_bid']['price']} on {best_prices['best_bid']['exchange']}")
        print(f"  -> Best Ask: {best_prices['best_ask']['price']} on {best_prices['best_ask']['exchange']}")
        
        # Calculate spread
        spread = best_prices['best_ask']['price'] - best_prices['best_bid']['price']
        spread_percent = (spread / best_prices['best_bid']['price']) * 100
        print(f"  -> Spread: {spread:.2f} ({spread_percent:.4f}%)")
    else:
        print("Could not retrieve prices from any exchange.")
    
    if best_prices.get('errors'):
        print(f"\nErrors encountered: {len(best_prices['errors'])}")

if __name__ == '__main__':
    # This allows the script to be run directly to test its functionality.
    asyncio.run(main())
