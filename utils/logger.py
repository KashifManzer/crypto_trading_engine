import logging
import os
import sys
from datetime import datetime
from typing import Optional

class TradingLogger:
    """
    Production-ready logging system for the crypto trading engine.
    Provides structured logging with different levels and file rotation.
    """
    
    def __init__(self, name: str = "trading_engine", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup console and file handlers with proper formatting."""
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler for all logs
        file_handler = logging.FileHandler(
            f"logs/trading_engine_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Error file handler
        error_handler = logging.FileHandler(
            f"logs/errors_{datetime.now().strftime('%Y%m%d')}.log"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: Optional[Exception] = None):
        """Log error message with optional exception info."""
        self.logger.error(message, exc_info=exc_info)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def critical(self, message: str, exc_info: Optional[Exception] = None):
        """Log critical message."""
        self.logger.critical(message, exc_info=exc_info)

# Global logger instance
logger = TradingLogger() 