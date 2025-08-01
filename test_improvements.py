#!/usr/bin/env python3
"""
Test script to verify the improvements (logging, rate limiting, error handling).
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from utils.logger import logger
from utils.rate_limiter import rate_limiter, retry_handler
from core.engine import TradingEngine

async def test_logging():
    """Test the logging system."""
    logger.info("Testing logging system...")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.info("✅ Logging system test completed")

async def test_rate_limiter():
    """Test the rate limiter."""
    logger.info("Testing rate limiter...")
    
    # Test rate limiting
    for i in range(5):
        allowed = await rate_limiter.acquire("binance", "test")
        logger.debug(f"Rate limit check {i+1}: {'allowed' if allowed else 'blocked'}")
    
    logger.info("✅ Rate limiter test completed")

async def test_retry_handler():
    """Test the retry handler."""
    logger.info("Testing retry handler...")
    
    # Test successful function
    async def successful_func():
        return "success"
    
    result = await retry_handler.execute_with_retry(successful_func)
    logger.info(f"Retry handler successful result: {result}")
    
    # Test failing function (will retry and eventually fail)
    async def failing_func():
        raise Exception("Test error")
    
    try:
        await retry_handler.execute_with_retry(failing_func)
    except Exception as e:
        logger.info(f"Retry handler correctly caught error: {e}")
    
    logger.info("✅ Retry handler test completed")

async def test_engine_with_logging():
    """Test the trading engine with logging."""
    logger.info("Testing trading engine with logging...")
    
    engine = TradingEngine()
    logger.info(f"Engine created with {len(engine.connectors)} connectors")
    
    if engine.connectors:
        logger.info("✅ Trading engine test completed")
    else:
        logger.warning("No connectors loaded (expected without API keys)")

async def main():
    """Run all improvement tests."""
    logger.info("🧪 Testing Improvements")
    logger.info("=" * 50)
    
    tests = [
        ("Logging System", test_logging),
        ("Rate Limiter", test_rate_limiter),
        ("Retry Handler", test_retry_handler),
        ("Trading Engine", test_engine_with_logging),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"--- {test_name} ---")
        try:
            await test_func()
            passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} failed: {e}")
    
    logger.info("=" * 50)
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All improvement tests passed!")
    else:
        logger.error("❌ Some improvement tests failed.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(asyncio.run(main())) 