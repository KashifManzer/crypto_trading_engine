import asyncio
import time
from typing import Dict, Optional
from collections import defaultdict
from utils.logger import logger

class RateLimiter:
    """
    Rate limiter to prevent API quota issues across different exchanges.
    Implements token bucket algorithm for fair rate limiting.
    """
    
    def __init__(self):
        # Rate limits per exchange (requests per minute)
        self.rate_limits = {
            'binance': 1200,  # 1200 requests per minute
            'kucoin': 1800,   # 1800 requests per minute
            'bybit': 120,     # 120 requests per minute
            'okx': 20,        # 20 requests per second
            'bitmart': 600,   # 600 requests per minute
            'huobi': 600,     # 600 requests per minute
            'coinbase': 30,   # 30 requests per second
        }
        
        # Track request timestamps for each exchange
        self.request_timestamps = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def acquire(self, exchange: str, request_type: str = "general") -> bool:
        """
        Acquire permission to make a request to the specified exchange.
        
        Args:
            exchange (str): Exchange name
            request_type (str): Type of request for logging
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        async with self.lock:
            current_time = time.time()
            exchange_lower = exchange.lower()
            
            # Get rate limit for this exchange
            rate_limit = self.rate_limits.get(exchange_lower, 60)  # Default 60 req/min
            
            # Clean old timestamps (older than 1 minute)
            self.request_timestamps[exchange_lower] = [
                ts for ts in self.request_timestamps[exchange_lower]
                if current_time - ts < 60
            ]
            
            # Check if we're within rate limit
            if len(self.request_timestamps[exchange_lower]) >= rate_limit:
                logger.warning(
                    f"Rate limit exceeded for {exchange_lower}. "
                    f"Limit: {rate_limit} req/min, "
                    f"Current: {len(self.request_timestamps[exchange_lower])}"
                )
                return False
            
            # Add current request timestamp
            self.request_timestamps[exchange_lower].append(current_time)
            logger.debug(f"Rate limit check passed for {exchange_lower} - {request_type}")
            return True
    
    async def wait_if_needed(self, exchange: str, request_type: str = "general") -> None:
        """
        Wait if necessary to respect rate limits.
        
        Args:
            exchange (str): Exchange name
            request_type (str): Type of request for logging
        """
        while not await self.acquire(exchange, request_type):
            logger.info(f"Rate limit hit for {exchange}, waiting...")
            await asyncio.sleep(1)  # Wait 1 second before retrying

class RetryHandler:
    """
    Handles retries with exponential backoff for failed API requests.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """
        Execute a function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    logger.error(
                        f"All retries exhausted for {func.__name__}. "
                        f"Final error: {str(e)}",
                        exc_info=e
                    )
                    raise
                
                # Calculate delay with exponential backoff
                delay = self.base_delay * (2 ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
        
        raise last_exception

# Global instances
rate_limiter = RateLimiter()
retry_handler = RetryHandler() 