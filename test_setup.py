#!/usr/bin/env python3
"""
Simple test script to verify the crypto trading engine setup.
This script will test basic functionality without requiring API keys.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from utils.logger import logger

def test_imports():
    """Test that all modules can be imported successfully."""
    logger.info("Testing imports...")
    
    try:
        from config import API_KEYS
        logger.info("✅ config.py imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import config.py: {e}")
        return False
    
    try:
        from connectors.base_connector import ExchangeConnector
        logger.info("✅ base_connector imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import base_connector: {e}")
        return False
    
    try:
        from core.engine import TradingEngine
        logger.info("✅ TradingEngine imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import TradingEngine: {e}")
        return False
    
    try:
        from core.symbol_mapper import SymbolMapper
        logger.info("✅ SymbolMapper imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import SymbolMapper: {e}")
        return False
    
    try:
        from utils.helpers import calculate_apr
        logger.info("✅ helpers imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import helpers: {e}")
        return False
    
    return True

def test_symbol_mapper():
    """Test the symbol mapper functionality."""
    logger.info("Testing symbol mapper...")
    
    try:
        from core.symbol_mapper import SymbolMapper
        mapper = SymbolMapper()
        
        # Test universal to exchange conversion
        universal = 'BTC/USDT'
        binance_symbol = mapper.to_exchange(universal, 'binance')
        kucoin_symbol = mapper.to_exchange(universal, 'kucoin')
        
        logger.info(f"✅ Universal '{universal}' -> Binance: '{binance_symbol}'")
        logger.info(f"✅ Universal '{universal}' -> KuCoin: '{kucoin_symbol}'")
        
        # Test exchange to universal conversion
        universal_from_binance = mapper.to_universal(binance_symbol, 'binance')
        universal_from_kucoin = mapper.to_universal(kucoin_symbol, 'kucoin')
        
        logger.info(f"✅ Binance '{binance_symbol}' -> Universal: '{universal_from_binance}'")
        logger.info(f"✅ KuCoin '{kucoin_symbol}' -> Universal: '{universal_from_kucoin}'")
        
        return True
    except Exception as e:
        logger.error(f"❌ Symbol mapper test failed: {e}")
        return False

def test_helpers():
    """Test the helper functions."""
    logger.info("Testing helper functions...")
    
    try:
        from utils.helpers import calculate_apr
        
        # Test APR calculation
        rate = 0.0001  # 0.01%
        frequency = 8   # 8 hours
        apr = calculate_apr(rate, frequency)
        
        logger.info(f"✅ APR calculation: {rate*100:.4f}% every {frequency}h = {apr:.2f}% APR")
        
        return True
    except Exception as e:
        logger.error(f"❌ Helper functions test failed: {e}")
        return False

async def test_engine():
    """Test the trading engine (without API keys)."""
    logger.info("Testing trading engine...")
    
    try:
        from core.engine import TradingEngine
        
        engine = TradingEngine()
        
        if not engine.connectors:
            logger.info("✅ Engine created successfully (no connectors loaded - expected without API keys)")
            return True
        else:
            logger.info(f"✅ Engine created with {len(engine.connectors)} connectors")
            return True
            
    except Exception as e:
        logger.error(f"❌ Trading engine test failed: {e}")
        return False

def test_file_structure():
    """Test that required files and directories exist."""
    logger.info("Testing file structure...")
    
    required_files = [
        'config.py',
        'requirements.txt',
        'README.md',
        'env.example',
        'connectors/__init__.py',
        'core/__init__.py',
        'utils/__init__.py',
        'scripts/__init__.py',
        'connectors/base_connector.py',
        'connectors/binance_connector.py',
        'core/engine.py',
        'core/symbol_mapper.py',
        'utils/helpers.py',
        'utils/logger.py',
        'utils/rate_limiter.py',
        'scripts/performance_test.py',
        'scripts/data_pipeline.py'
    ]
    
    required_dirs = [
        'data',
        'connectors',
        'core',
        'utils',
        'scripts'
    ]
    
    all_good = True
    
    for file_path in required_files:
        if os.path.exists(file_path):
            logger.info(f"✅ {file_path}")
        else:
            logger.error(f"❌ Missing: {file_path}")
            all_good = False
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            logger.info(f"✅ {dir_path}/")
        else:
            logger.error(f"❌ Missing directory: {dir_path}/")
            all_good = False
    
    return all_good

def main():
    """Run all tests."""
    logger.info("🧪 Crypto Trading Engine Setup Test")
    logger.info("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Imports", test_imports),
        ("Symbol Mapper", test_symbol_mapper),
        ("Helper Functions", test_helpers),
        ("Trading Engine", lambda: asyncio.run(test_engine()))
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"--- {test_name} ---")
        if test_func():
            passed += 1
        else:
            logger.error(f"❌ {test_name} failed")
    
    logger.info("=" * 50)
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! The project is ready to use.")
        logger.info("Next steps:")
        logger.info("1. Copy env.example to .env")
        logger.info("2. Add your API keys to .env")
        logger.info("3. Run: python -m core.engine")
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 