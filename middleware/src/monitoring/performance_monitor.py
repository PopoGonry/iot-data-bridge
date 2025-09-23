"""
Performance Monitor for SignalR Middleware
"""

import asyncio
import time
import psutil
from typing import Dict, Any, Optional
import structlog
from collections import defaultdict, deque
from datetime import datetime, timedelta


class PerformanceMonitor:
    """Performance monitoring for SignalR middleware"""
    
    def __init__(self, enable_metrics: bool = True, metrics_interval: int = 60):
        self.enable_metrics = enable_metrics
        self.metrics_interval = metrics_interval
        self.logger = structlog.get_logger("performance_monitor")
        
        # Performance counters
        self.message_count = 0
        self.batch_count = 0
        self.error_count = 0
        self.connection_count = 0
        self.start_time = time.time()
        
        # Historical data
        self.message_history = deque(maxlen=1000)
        self.batch_history = deque(maxlen=1000)
        self.error_history = deque(maxlen=1000)
        
        # Layer performance tracking
        self.layer_stats = defaultdict(lambda: {
            'processed': 0,
            'errors': 0,
            'avg_processing_time': 0.0,
            'last_activity': None
        })
        
        self._monitoring_task = None
        
    async def start(self):
        """Start performance monitoring"""
        if self.enable_metrics:
            self._monitoring_task = asyncio.create_task(self._monitor_performance())
            self.logger.info("Performance monitoring started")
    
    async def stop(self):
        """Stop performance monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Performance monitoring stopped")
    
    def record_message(self, layer: str = "unknown"):
        """Record a processed message"""
        self.message_count += 1
        self.message_history.append({
            'timestamp': time.time(),
            'layer': layer
        })
        self.layer_stats[layer]['processed'] += 1
        self.layer_stats[layer]['last_activity'] = time.time()
    
    def record_batch(self, batch_size: int, layer: str = "unknown"):
        """Record a processed batch"""
        self.batch_count += 1
        self.batch_history.append({
            'timestamp': time.time(),
            'batch_size': batch_size,
            'layer': layer
        })
    
    def record_error(self, layer: str = "unknown"):
        """Record an error"""
        self.error_count += 1
        self.error_history.append({
            'timestamp': time.time(),
            'layer': layer
        })
        self.layer_stats[layer]['errors'] += 1
    
    def record_connection(self):
        """Record a new connection"""
        self.connection_count += 1
    
    def record_processing_time(self, layer: str, processing_time: float):
        """Record processing time for a layer"""
        current_avg = self.layer_stats[layer]['avg_processing_time']
        processed = self.layer_stats[layer]['processed']
        
        # Calculate new average
        new_avg = ((current_avg * (processed - 1)) + processing_time) / processed
        self.layer_stats[layer]['avg_processing_time'] = new_avg
    
    async def _monitor_performance(self):
        """Monitor performance metrics"""
        while True:
            try:
                await asyncio.sleep(self.metrics_interval)
                await self._log_performance_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in performance monitoring", error=str(e))
    
    async def _log_performance_metrics(self):
        """Log performance metrics"""
        try:
            uptime = time.time() - self.start_time
            
            # Calculate rates
            message_rate = self.message_count / uptime if uptime > 0 else 0
            batch_rate = self.batch_count / uptime if uptime > 0 else 0
            error_rate = self.error_count / uptime if uptime > 0 else 0
            
            # System metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / 1024 / 1024
            
            # Recent activity (last 5 minutes)
            recent_cutoff = time.time() - 300
            recent_messages = sum(1 for msg in self.message_history if msg['timestamp'] > recent_cutoff)
            recent_batches = sum(1 for batch in self.batch_history if batch['timestamp'] > recent_cutoff)
            recent_errors = sum(1 for err in self.error_history if err['timestamp'] > recent_cutoff)
            
            metrics = {
                'uptime_seconds': uptime,
                'total_messages': self.message_count,
                'total_batches': self.batch_count,
                'total_errors': self.error_count,
                'active_connections': self.connection_count,
                'message_rate_per_second': message_rate,
                'batch_rate_per_second': batch_rate,
                'error_rate_per_second': error_rate,
                'recent_messages_5min': recent_messages,
                'recent_batches_5min': recent_batches,
                'recent_errors_5min': recent_errors,
                'system_cpu_percent': cpu_percent,
                'system_memory_percent': memory_percent,
                'system_memory_used_mb': memory_used_mb,
                'layer_stats': dict(self.layer_stats)
            }
            
            self.logger.info("Performance metrics", **metrics)
            
        except Exception as e:
            self.logger.error("Error logging performance metrics", error=str(e))
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': uptime,
            'total_messages': self.message_count,
            'total_batches': self.batch_count,
            'total_errors': self.error_count,
            'active_connections': self.connection_count,
            'message_rate_per_second': self.message_count / uptime if uptime > 0 else 0,
            'batch_rate_per_second': self.batch_count / uptime if uptime > 0 else 0,
            'error_rate_per_second': self.error_count / uptime if uptime > 0 else 0,
            'system_cpu_percent': psutil.cpu_percent(),
            'system_memory_percent': psutil.virtual_memory().percent,
            'layer_stats': dict(self.layer_stats)
        }
