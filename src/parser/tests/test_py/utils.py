"""Utility functions and classes"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)

class Logger:
    """Custom logger class"""
    
    def __init__(self, name: str = "default"):
        """Initialize logger"""
        self.name = name
        self.logger = logging.getLogger(name)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(f"[{self.name}] {message}")
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(f"[{self.name}] {message}")
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(f"[{self.name}] {message}")

# Global logger instance
logger = Logger("app")

def format_date(date: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime object"""
    return date.strftime(format_str)

def validate_email(email: str) -> bool:
    """Simple email validation"""
    return "@" in email and "." in email

def process_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process a list of data dictionaries"""
    processed = []
    for item in data:
        # Call validation function
        if 'email' in item and validate_email(item['email']):
            processed.append(item)
        # Log processing
        logger.debug(f"Processed item: {item.get('id', 'unknown')}")
    
    return processed

class DataProcessor:
    """Data processing class"""
    
    def __init__(self, batch_size: int = 100):
        """Initialize processor"""
        self.batch_size = batch_size
        self.processed_count = 0
    
    def process_batch(self, batch: List[Any]) -> List[Any]:
        """Process a batch of data"""
        # Use utility function
        if isinstance(batch[0], dict):
            result = process_data(batch)
        else:
            result = batch
        
        self.processed_count += len(result)
        # Log using global logger
        logger.info(f"Processed batch of {len(result)} items")
        
        return result
    
    @staticmethod
    def create_default():
        """Create processor with default settings"""
        return DataProcessor(batch_size=50)