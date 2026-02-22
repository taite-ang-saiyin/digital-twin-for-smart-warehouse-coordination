"""
Logging utilities for robot agents
"""

import logging
import os
from datetime import datetime
from typing import Optional

def setup_logger(name: str, log_file: Optional[str] = None, level=logging.INFO):
    """
    Set up a logger with file and console handlers
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Logging level
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log_file specified)
    if log_file:
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

class RobotLogger:
    """Specialized logger for robot actions"""
    
    def __init__(self, robot_id: str):
        self.robot_id = robot_id
        self.logger = logging.getLogger(f"robot.{robot_id}")
        self.actions = []
    
    def log_action(self, action: str, details: dict = None):
        """Log a robot action"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'robot_id': self.robot_id,
            'action': action,
            'details': details or {}
        }
        self.actions.append(log_entry)
        self.logger.info(f"{action}: {details}")
    
    def get_action_history(self) -> list:
        """Get all logged actions"""
        return self.actions.copy()
    
    def clear_history(self):
        """Clear action history"""
        self.actions.clear()