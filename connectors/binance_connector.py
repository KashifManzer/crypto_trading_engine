import aiohttp
import time
import hmac
import hashlib
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode

from .base_connector import ExchangeConnector
from core.symbol_mapper import SymbolMapper

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
        """Makes an asynchronous HTTP request to the exchange."""
        if params is None:
            params = {}

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._sign_request(params)

        headers = {'X-MBX-APIKEY': self.api_key} if signed else {}
        url = f"{base_url}{path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, params=params, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Error from {self.name}: {response.status} - {error_text}")
                response.raise_for_status()
                return await response.json()

    async def get_best_bid_ask(self, pair: str) -> Dict[str, float]:
        exchange_pair = self.mapper.to_exchange(pair, self.name)
        data = await self._request("GET", self.BASE_URL_SPOT, "/ticker/bookTicker", {"symbol": exchange_pair})
        return {"bid": float(data["bidPrice"]), "ask": float(data["askPrice"])}

    async def get_l2_order_book(self, pair: str) -> Dict[str, List[List[float]]]:
        exchange_pair = self.mapper.to_exchange(pair, self.name)
        params = {"symbol": exchange_pair, "limit": 1000}
        data = await self._request("GET", self.BASE_URL_SPOT, "/depth", params)
        return {
            "bids": [[float(p), float(q)] for p, q in data["bids"]],
            "asks": [[float(p), float(q)] for p, q in data["asks"]],
        }

    async def get_funding_rates(self, pair: str) -> Dict[str, Any]:
        exchange_pair = self.mapper.to_exchange(pair, self.name)
        # Funding rate is a futures concept
        params = {"symbol": exchange_pair}
        data = await self._request("GET", self.BASE_URL_FUTURES, "/premiumIndex", params)
        
        # Historical data would require another call to /fundingRate
        # For simplicity, we focus on the live and predicted rate here.
        return {
            "current_rate": float(data["lastFundingRate"]),
            "predicted_rate": float(data["lastFundingRate"]), # Binance API combines these
            "historical": [] # Placeholder
        }

    async def calculate_price_impact(self, pair: str, side: str, trade_volume_quote: float) -> Dict[str, float]:
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
        
        return {
            "average_execution_price": avg_exec_price,
            "price_impact_percent": price_impact
        }

    async def place_order(self, pair: str, side: str, quantity: float, order_type: str, price: Optional[float] = None) -> Dict[str, Any]:
        exchange_pair = self.mapper.to_exchange(pair, self.name)
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
        return {"order_id": data["orderId"], "client_order_id": data["clientOrderId"], "data": data}

    async def cancel_order(self, order_id: str, pair: str) -> Dict[str, Any]:
        exchange_pair = self.mapper.to_exchange(pair, self.name)
        params = {"symbol": exchange_pair, "orderId": order_id}
        data = await self._request("DELETE", self.BASE_URL_SPOT, "/order", params, signed=True)
        return {"status": data["status"], "data": data}

    async def get_order_status(self, order_id: str, pair: str) -> Dict[str, Any]:
        exchange_pair = self.mapper.to_exchange(pair, self.name)
        params = {"symbol": exchange_pair, "orderId": order_id}
        data = await self._request("GET", self.BASE_URL_SPOT, "/order", params, signed=True)
        return {
            "status": data["status"],
            "filled_quantity": float(data["executedQty"]),
            "avg_fill_price": float(data.get("cummulativeQuoteQty", 0)) / float(data["executedQty"]) if float(data["executedQty"]) > 0 else 0,
            "data": data
        }

    async def get_position_details(self, filled_order: Dict[str, Any]) -> Dict[str, Any]:
        # This is a simplified example. A real implementation would need to track positions
        # based on account data, as spot trades don't create "positions" in the same way
        # as futures. This function simulates it based on the entry trade.
        pair = filled_order['pair']
        entry_price = filled_order['avg_fill_price']
        quantity = filled_order['quantity']
        side = filled_order['side']

        # Get current market price to calculate unrealized PnL
        current_price_info = await self.get_best_bid_ask(pair)
        current_price = (current_price_info['bid'] + current_price_info['ask']) / 2
        
        pnl = 0
        if side.lower() == 'long' or side.lower() == 'buy':
            pnl = (current_price - entry_price) * quantity
        else: # short/sell
            pnl = (entry_price - current_price) * quantity

        return {
            "connector_name": self.name,
            "pair_name": pair,
            "entry_timestamp": filled_order.get('timestamp', time.time()),
            "entry_price": entry_price,
            "quantity": quantity,
            "position_side": side,
            "NetPnL": pnl
        }
