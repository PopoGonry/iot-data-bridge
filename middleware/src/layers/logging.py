"""
Logging Layer - Handles event logging (Optimized)
"""

import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, List, Dict
import structlog
from collections import deque
from datetime import datetime
import aiofiles

from layers.base import LoggingLayerInterface
from models.events import MiddlewareEventLog, DeviceIngestLog
from models.config import LoggingConfig


class OptimizedLoggingLayer(LoggingLayerInterface):
    """Optimized Logging Layer with batch processing and async I/O"""
    
    def __init__(self, config: LoggingConfig):
        super().__init__("logging_layer")
        self.config = config
        self.logger = structlog.get_logger("logging_layer")
        self._setup_file_logging()
        
        # Performance optimizations
        self.log_queue = deque(maxlen=10000)  # Log message queue
        self.batch_size = getattr(config, 'log_batch_size', 100)
        self.flush_interval = getattr(config, 'log_flush_interval', 1.0)
        self.enable_async_logging = getattr(config, 'enable_async_logging', True)
        self._batch_task = None
        self._file_handle = None
        
    def _setup_file_logging(self):
        """Setup optimized file logging with timestamped files"""
        # Create logs directory if it doesn't exist
        log_file = Path(self.config.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_name = log_file.stem
        log_ext = log_file.suffix
        timestamped_log_file = log_file.parent / f"{log_name}_{timestamp}{log_ext}"
        
        # Store the timestamped log file path
        self.timestamped_log_file = timestamped_log_file
        
        # Setup rotating file handler for better performance
        self.file_handler = RotatingFileHandler(
            timestamped_log_file,
            maxBytes=self.config.max_size,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        self.file_handler.setLevel(logging.INFO)
    
    async def start(self):
        """Start logging layer with batch processing"""
        self.is_running = True
        
        if self.enable_async_logging:
            # Start batch processing task
            self._batch_task = asyncio.create_task(self._process_log_batch())
            # Silent startup
    
    async def stop(self):
        """Stop logging layer and flush remaining logs"""
        self.is_running = False
        
        if self._batch_task:
            # Flush remaining logs
            await self._flush_logs()
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
        
        if self._file_handle:
            await self._file_handle.close()
    
    async def log_middleware_event(self, event: MiddlewareEventLog):
        """Log middleware event with data transmission details"""
        try:
            self._increment_processed()
            
            # Create detailed middleware log message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"{timestamp} | INFO | Data processed | trace_id={event.trace_id} | object={event.object} | target_devices={','.join(event.send_devices)}"
            
            if self.enable_async_logging:
                # Add to batch queue
                self.log_queue.append(log_message)
            else:
                # Direct logging (fallback)
                await self._write_log_direct(log_message)
            
        except Exception as e:
            self._increment_error()
    
    async def log_device_ingest(self, event: DeviceIngestLog):
        """Log device ingest event with optimized batching"""
        try:
            self._increment_processed()
            
            # Create log message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"{timestamp} | INFO | Data sent | device_id={event.device_id} | object={event.object} | value={event.value}"
            
            if self.enable_async_logging:
                # Add to batch queue
                self.log_queue.append(log_message)
            else:
                # Direct logging (fallback)
                await self._write_log_direct(log_message)
            
        except Exception as e:
            self._increment_error()
    
    async def _process_log_batch(self):
        """Process log messages in batches for better performance"""
        while self.is_running:
            try:
                if not self.log_queue:
                    await asyncio.sleep(self.flush_interval)
                    continue
                
                # Collect batch of log messages
                batch = []
                for _ in range(min(self.batch_size, len(self.log_queue))):
                    if self.log_queue:
                        batch.append(self.log_queue.popleft())
                
                if batch:
                    await self._write_log_batch(batch)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in batch processing", error=str(e))
                await asyncio.sleep(0.1)
    
    async def _write_log_batch(self, batch: List[str]):
        """Write batch of log messages efficiently"""
        try:
            # Prepare batch content
            batch_content = '\n'.join(batch) + '\n'
            
            # Async file write to timestamped log file
            async with aiofiles.open(self.timestamped_log_file, 'a', encoding='utf-8') as f:
                await f.write(batch_content)
                await f.flush()
            
            # Console output (reduced frequency for performance)
            if len(batch) >= 10:  # Only show console logs for larger batches
                for message in batch[:5]:  # Show first 5 messages
                    print(message)
                if len(batch) > 5:
                    print(f"... and {len(batch) - 5} more messages")
            else:
                for message in batch:
                    print(message)
                    
        except Exception as e:
            self.logger.error("Error writing log batch", error=str(e))
    
    async def _write_log_direct(self, message: str):
        """Direct log writing (fallback)"""
        try:
            async with aiofiles.open(self.timestamped_log_file, 'a', encoding='utf-8') as f:
                await f.write(message + '\n')
                await f.flush()
            
            print(message)
            
        except Exception as e:
            self.logger.error("Error writing log directly", error=str(e))
    
    async def _flush_logs(self):
        """Flush all remaining logs"""
        if self.log_queue:
            batch = list(self.log_queue)
            self.log_queue.clear()
            await self._write_log_batch(batch)


# Use OptimizedLoggingLayer directly
LoggingLayer = OptimizedLoggingLayer