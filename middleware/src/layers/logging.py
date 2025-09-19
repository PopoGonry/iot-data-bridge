"""
Logging Layer - Handles event logging
"""

import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
import structlog

from layers.base import LoggingLayerInterface
from models.events import MiddlewareEventLog, DeviceIngestLog
from models.config import LoggingConfig


class LoggingLayer(LoggingLayerInterface):
    """Logging Layer - Handles event logging"""
    
    def __init__(self, config: LoggingConfig):
        super().__init__("logging_layer")
        self.config = config
        self.logger = structlog.get_logger("logging_layer")
        self._setup_file_logging()
    
    def _setup_file_logging(self):
        """Setup file logging"""
        # Create logs directory if it doesn't exist
        log_file = Path(self.config.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # No need to setup structlog handler - we write directly to file in log_device_ingest
    
    async def start(self):
        """Start logging layer"""
        self.is_running = True
    
    async def stop(self):
        """Stop logging layer"""
        self.is_running = False
    
    async def log_middleware_event(self, event: MiddlewareEventLog):
        """Log middleware event - disabled to avoid duplicate logs"""
        try:
            self._increment_processed()
            # Do nothing - we only want device_ingest logs
            pass
        except Exception as e:
            self._increment_error()
            # Don't log the error to avoid console spam
    
    async def log_device_ingest(self, event: DeviceIngestLog):
        """Log device ingest event"""
        try:
            self._increment_processed()
            
            # Create log message in the requested format
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"{timestamp} | INFO | Data sent | device_id={event.device_id} | object={event.object} | value={event.value}"
            
            # Write to log file
            log_file = Path(self.config.file)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
                f.flush()
            
            # Also log to console in the requested format
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} | INFO | Data sent | device_id={event.device_id} | object={event.object} | value={event.value}")
            
        except Exception as e:
            self._increment_error()
    
    async def _write_log(self, log_data: dict):
        """Write log data to file"""
        try:
            # Convert to JSON string
            log_line = json.dumps(log_data, ensure_ascii=False) + '\n'
            
            # Write to file (async file I/O)
            log_file = Path(self.config.file)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
                f.flush()
            
        except Exception as e:
            self.logger.error("Error writing to log file", error=str(e))