from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from utils.logger import logger
from utils.rate_limiter import rate_limiter, retry_handler

class ExchangeConnector(ABC):
    """
    Abstract Base Class for exchange connectors.
    Defines a standard interface that all exchange-specific connectors must implement.
    This ensures modularity and consistency across the application.
    """

    def __init__(self, api_key: str, api_secret: str, **kwargs):
        """
        Initializes the connector with API credentials.
        
        Args:
            api_key (str): The API key for the exchange.
            api_secret (str): The API secret for the exchange.
            **kwargs: Additional credentials like passphrase or memo.
        """
        if not api_key or not api_secret:
            logger.error(f"API key and secret must be provided for {self.__class__.__name__}")
            raise ValueError(f"API key and secret must be provided for {self.__class__.__name__}")
            
        self.api_key = api_key
        self.api_secret = api_secret
        self.name = self.__class__.__name__.replace("Connector", "").lower()
        # Store any other credentials passed
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        logger.info(f"Initialized {self.__class__.__name__} connector")

    @abstractmethod
    async def get_best_bid_ask(self, pair: str) -> Dict[str, float]:
        """
        Get the current best bid and ask prices for a given trading pair.
        
        Args:
            pair (str): The universal symbol for the trading pair (e.g., 'BTC/USDT').
            
        Returns:
            A dictionary with 'bid' and 'ask' keys. e.g., {'bid': 60000.1, 'ask': 60000.2}
        """
        pass

    @abstractmethod
    async def get_l2_order_book(self, pair: str) -> Dict[str, List[List[float]]]:
        """
        Retrieve the full-depth L2 order book.
        
        Args:
            pair (str): The universal symbol for the trading pair.
            
        Returns:
            A dictionary with 'bids' and 'asks' lists.
            e.g., {'bids': [[price, quantity], ...], 'asks': [[price, quantity], ...]}
        """
        pass

    @abstractmethod
    async def get_funding_rates(self, pair: str) -> Dict[str, Any]:
        """
        Fetch live, predicted, and historical funding rates for perpetual contracts.
        
        Args:
            pair (str): The universal symbol for the trading pair.
            
        Returns:
            A dictionary containing current, predicted, and historical rates.
            e.g., {'current_rate': 0.0001, 'predicted_rate': 0.00012, 'historical': [...]}
        """
        pass

    @abstractmethod
    async def calculate_price_impact(self, pair: str, side: str, trade_volume_quote: float) -> Dict[str, float]:
        """
        Calculate the effective execution price and price impact for a given volume.
        
        Args:
            pair (str): The universal symbol for the trading pair.
            side (str): 'buy' or 'sell'.
            trade_volume_quote (float): The volume of the trade in the quote currency (e.g., 50000 USDT).
            
        Returns:
            A dictionary with average execution price and price impact percentage.
            e.g., {'average_execution_price': 60050.5, 'price_impact_percent': 0.084}
        """
        pass

    @abstractmethod
    async def place_order(self, pair: str, side: str, quantity: float, order_type: str, price: Optional[float] = None) -> Dict[str, Any]:
        """
        Place a LIMIT or MARKET order.
        
        Args:
            pair (str): The universal symbol for the trading pair.
            side (str): 'buy' or 'sell'.
            quantity (float): The amount of the base currency to trade.
            order_type (str): 'LIMIT' or 'MARKET'.
            price (Optional[float]): The price for a LIMIT order.
            
        Returns:
            A dictionary containing the exchange-provided order ID.
            e.g., {'order_id': '123456789'}
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, pair: str) -> Dict[str, Any]:
        """
        Cancel an open order using its Order ID.
        
        Args:
            order_id (str): The unique order ID provided by the exchange.
            pair (str): The universal symbol for the trading pair.
            
        Returns:
            A dictionary confirming the cancellation. e.g., {'status': 'CANCELED'}
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str, pair: str) -> Dict[str, Any]:
        """
        Get the current status of an order.
        
        Args:
            order_id (str): The unique order ID provided by the exchange.
            pair (str): The universal symbol for the trading pair.
            
        Returns:
            A dictionary with the order's status.
            e.g., {'status': 'FILLED', 'filled_quantity': 0.1, ...}
        """
        pass
    
    @abstractmethod
    async def get_position_details(self, filled_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch position details using the data from a filled entry order.
        
        Args:
            filled_order (Dict[str, Any]): A dictionary representing a filled order,
                                           containing at least 'pair', 'side', 'quantity', 'avg_fill_price'.
                                           
        Returns:
            A structured object with live position details including real-time PnL.
        """
        pass
