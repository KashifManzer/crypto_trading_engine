import aiohttp
import time
import hmac
import hashlib
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode

from .base_connector import ExchangeConnector
from core.symbol_mapper import SymbolMapper
from utils.logger import logger
from utils.rate_limiter import rate_limiter, retry_handler

class BinanceConnector(ExchangeConnector):
    """Concrete implementation for the Binance exchange (Spot and Futures)."""

    BASE_URL_SPOT = "https://api.binance.com/api/v3"
    BASE_URL_FUTURES = "https://fapi.binance.com/fapi/v1"

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.mapper = SymbolMapper()

    def _sign_request(self, params: Dict[str, Any]) -> str:
        """Signs the request payload."""
        query_string = urlencode(params)
        return hmac.new(self.api_secret.encode('utf-8'), msg=query_string.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()

    async def _request(self, method: str, base_url: str, path: str, params: Optional[Dict] = None, signed: bool = False):
        """Makes an asynchronous HTTP request to the exchange with rate limiting and retry logic."""
        
        async def _make_request():
            # Wait for rate limit
            await rate_limiter.wait_if_needed(self.name, f"{method}_{path}")
            
            if params is None:
                params = {}

            if signed:
                params['timestamp'] = int(time.time() * 1000)
                params['signature'] = self._sign_request(params)

            headers = {'X-MBX-APIKEY': self.api_key} if signed else {}
            url = f"{base_url}{path}"
            
            logger.debug(f"Making {method} request to {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, params=params, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"HTTP {response.status} error from {self.name}: {error_text}")
                        
                        # Handle specific error cases
                        if response.status == 429:
                            raise Exception(f"Rate limit exceeded for {self.name}")
                        elif response.status == 401:
                            raise Exception(f"Authentication failed for {self.name}")
                        elif response.status == 403:
                            raise Exception(f"Permission denied for {self.name}")
                        else:
                            raise Exception(f"HTTP {response.status}: {error_text}")
                    
                    response.raise_for_status()
                    return await response.json()
        
        # Execute with retry logic
        return await retry_handler.execute_with_retry(_make_request)

    async def get_best_bid_ask(self, pair: str) -> Dict[str, float]:
        try:
            exchange_pair = self.mapper.to_exchange(pair, self.name)
            logger.debug(f"Fetching best bid/ask for {pair} on {self.name}")
            data = await self._request("GET", self.BASE_URL_SPOT, "/ticker/bookTicker", {"symbol": exchange_pair})
            result = {"bid": float(data["bidPrice"]), "ask": float(data["askPrice"])}
            logger.debug(f"Best bid/ask for {pair}: bid={result['bid']}, ask={result['ask']}")
            return result
        except Exception as e:
            logger.error(f"Failed to get best bid/ask for {pair} on {self.name}: {str(e)}")
            raise

    async def get_l2_order_book(self, pair: str) -> Dict[str, List[List[float]]]:
        try:
            exchange_pair = self.mapper.to_exchange(pair, self.name)
            logger.debug(f"Fetching L2 order book for {pair} on {self.name}")
            params = {"symbol": exchange_pair, "limit": 1000}
            data = await self._request("GET", self.BASE_URL_SPOT, "/depth", params)
            result = {
                "bids": [[float(p), float(q)] for p, q in data["bids"]],
                "asks": [[float(p), float(q)] for p, q in data["asks"]],
            }
            logger.debug(f"L2 order book for {pair}: {len(result['bids'])} bids, {len(result['asks'])} asks")
            return result
        except Exception as e:
            logger.error(f"Failed to get L2 order book for {pair} on {self.name}: {str(e)}")
            raise

    async def get_funding_rates(self, pair: str) -> Dict[str, Any]:
        try:
            exchange_pair = self.mapper.to_exchange(pair, self.name)
            logger.debug(f"Fetching funding rates for {pair} on {self.name}")
            # Funding rate is a futures concept
            params = {"symbol": exchange_pair}
            data = await self._request("GET", self.BASE_URL_FUTURES, "/premiumIndex", params)
            
            # Historical data would require another call to /fundingRate
            # For simplicity, we focus on the live and predicted rate here.
            result = {
                "current_rate": float(data["lastFundingRate"]),
                "predicted_rate": float(data["lastFundingRate"]), # Binance API combines these
                "historical": [] # Placeholder
            }
            logger.debug(f"Funding rates for {pair}: current={result['current_rate']}, predicted={result['predicted_rate']}")
            return result
        except Exception as e:
            logger.error(f"Failed to get funding rates for {pair} on {self.name}: {str(e)}")
            raise

    async def calculate_price_impact(self, pair: str, side: str, trade_volume_quote: float) -> Dict[str, float]:
        try:
            logger.debug(f"Calculating price impact for {pair} {side} {trade_volume_quote} USDT on {self.name}")
            order_book = await self.get_l2_order_book(pair)
            best_bid_ask = await self.get_best_bid_ask(pair)
            mid_price = (best_bid_ask['bid'] + best_bid_ask['ask']) / 2
            
            book_side = order_book['asks'] if side.lower() == 'buy' else order_book['bids']
            
            volume_to_fill = trade_volume_quote
            filled_value = 0
            filled_quantity = 0

            for price, quantity in book_side:
                level_value = price * quantity
                if volume_to_fill <= level_value:
                    filled_quantity += volume_to_fill / price
                    filled_value += volume_to_fill
                    break
                else:
                    volume_to_fill -= level_value
                    filled_value += level_value
                    filled_quantity += quantity
            
            if filled_value < trade_volume_quote * 0.999: # Allow for small precision errors
                 raise ValueError("Not enough liquidity in the order book to fill the trade.")

            avg_exec_price = filled_value / filled_quantity
            price_impact = ((avg_exec_price - mid_price) / mid_price) * 100
            
            result = {
                "average_execution_price": avg_exec_price,
                "price_impact_percent": price_impact
            }
            logger.debug(f"Price impact calculation: avg_price={avg_exec_price}, impact={price_impact}%")
            return result
        except Exception as e:
            logger.error(f"Failed to calculate price impact for {pair} on {self.name}: {str(e)}")
            raise

    async def place_order(self, pair: str, side: str, quantity: float, order_type: str, price: Optional[float] = None) -> Dict[str, Any]:
        try:
            exchange_pair = self.mapper.to_exchange(pair, self.name)
            logger.info(f"Placing {order_type} {side} order for {quantity} {pair} on {self.name}")
            
            params = {
                "symbol": exchange_pair,
                "side": side.upper(),
                "type": order_type.upper(),
                "quantity": quantity,
            }
            if order_type.upper() == 'LIMIT':
                if price is None:
                    raise ValueError("Price is required for LIMIT orders.")
                params["timeInForce"] = "GTC" # Good 'Til Canceled
                params["price"] = price
            
            # Using spot endpoint for this example
            data = await self._request("POST", self.BASE_URL_SPOT, "/order", params, signed=True)
            result = {"order_id": data["orderId"], "client_order_id": data["clientOrderId"], "data": data}
            logger.info(f"Order placed successfully: {result['order_id']}")
            return result
        except Exception as e:
            logger.error(f"Failed to place order for {pair} on {self.name}: {str(e)}")
            raise

    async def cancel_order(self, order_id: str, pair: str) -> Dict[str, Any]:
        try:
            exchange_pair = self.mapper.to_exchange(pair, self.name)
            logger.info(f"Canceling order {order_id} for {pair} on {self.name}")
            params = {"symbol": exchange_pair, "orderId": order_id}
            data = await self._request("DELETE", self.BASE_URL_SPOT, "/order", params, signed=True)
            result = {"status": data["status"], "data": data}
            logger.info(f"Order {order_id} canceled successfully")
            return result
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id} on {self.name}: {str(e)}")
            raise

    async def get_order_status(self, order_id: str, pair: str) -> Dict[str, Any]:
        try:
            exchange_pair = self.mapper.to_exchange(pair, self.name)
            logger.debug(f"Getting status for order {order_id} on {self.name}")
            params = {"symbol": exchange_pair, "orderId": order_id}
            data = await self._request("GET", self.BASE_URL_SPOT, "/order", params, signed=True)
            result = {
                "status": data["status"],
                "filled_quantity": float(data["executedQty"]),
                "avg_fill_price": float(data.get("cummulativeQuoteQty", 0)) / float(data["executedQty"]) if float(data["executedQty"]) > 0 else 0,
                "data": data
            }
            logger.debug(f"Order {order_id} status: {result['status']}, filled: {result['filled_quantity']}")
            return result
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id} on {self.name}: {str(e)}")
            raise

    async def get_position_details(self, filled_order: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # This is a simplified example. A real implementation would need to track positions
            # based on account data, as spot trades don't create "positions" in the same way
            # as futures. This function simulates it based on the entry trade.
            pair = filled_order['pair']
            entry_price = filled_order['avg_fill_price']
            quantity = filled_order['quantity']
            side = filled_order['side']

            logger.debug(f"Getting position details for {pair} on {self.name}")

            # Get current market price to calculate unrealized PnL
            current_price_info = await self.get_best_bid_ask(pair)
            current_price = (current_price_info['bid'] + current_price_info['ask']) / 2
            
            pnl = 0
            if side.lower() == 'long' or side.lower() == 'buy':
                pnl = (current_price - entry_price) * quantity
            else: # short/sell
                pnl = (entry_price - current_price) * quantity

            result = {
                "connector_name": self.name,
                "pair_name": pair,
                "entry_timestamp": filled_order.get('timestamp', time.time()),
                "entry_price": entry_price,
                "quantity": quantity,
                "position_side": side,
                "NetPnL": pnl
            }
            logger.debug(f"Position details: PnL={pnl}, entry_price={entry_price}, current_price={current_price}")
            return result
        except Exception as e:
            logger.error(f"Failed to get position details on {self.name}: {str(e)}")
            raise
