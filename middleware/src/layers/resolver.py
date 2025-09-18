"""
Resolver Layer - Resolves mapped events to target devices
"""

import asyncio
from typing import Optional, Callable
import structlog

from src.layers.base import ResolverLayerInterface
from src.models.events import MappedEvent, ResolvedEvent, MiddlewareEventLog
from src.catalogs.device_catalog import DeviceCatalog


class ResolverLayer(ResolverLayerInterface):
    """Resolver Layer - Resolves MappedEvent to target devices"""
    
    def __init__(self, device_catalog: DeviceCatalog, logging_callback: Callable[[MiddlewareEventLog], None]):
        super().__init__("resolver_layer")
        self.device_catalog = device_catalog
        self.logging_callback = logging_callback
        self.transports_callback = None
    
    def set_transports_callback(self, callback: Callable[[ResolvedEvent], None]):
        """Set transports layer callback"""
        self.transports_callback = callback
    
    async def start(self):
        """Start resolver layer"""
        self.logger.info("Starting resolver layer")
        self.is_running = True
        self.logger.info("Resolver layer started")
    
    async def stop(self):
        """Stop resolver layer"""
        self.logger.info("Stopping resolver layer")
        self.is_running = False
        self.logger.info("Resolver layer stopped")
    
    async def resolve_event(self, event: MappedEvent) -> Optional[ResolvedEvent]:
        """Resolve mapped event to target devices"""
        try:
            self._increment_processed()
            
            self.logger.debug("Resolving event", 
                            trace_id=event.trace_id,
                            object=event.object)
            
            # Get target devices for the object
            target_devices = self.device_catalog.get_devices_for_object(event.object)
            
            if not target_devices:
                self.logger.warning("No target devices found for object",
                                  trace_id=event.trace_id,
                                  object=event.object)
                self._increment_error()
                return None
            
            # Create resolved event
            resolved_event = ResolvedEvent(
                trace_id=event.trace_id,
                object=event.object,
                value=event.value,
                target_devices=target_devices
            )
            
            self.logger.debug("Successfully resolved event",
                            trace_id=event.trace_id,
                            object=event.object,
                            target_devices=target_devices)
            
            # Log middleware event
            await self._log_middleware_event(event, target_devices)
            
            # Forward to transports layer
            if self.transports_callback:
                await self.transports_callback(resolved_event)
            
            return resolved_event
            
        except Exception as e:
            self._increment_error()
            self.logger.error("Error resolving event", 
                            error=str(e), 
                            trace_id=event.trace_id)
            return None
    
    async def _log_middleware_event(self, event: MappedEvent, target_devices: list):
        """Log middleware event"""
        try:
            # Create middleware event log
            middleware_log = MiddlewareEventLog(
                trace_id=event.trace_id,
                raw={},  # We don't have access to raw data here
                object=event.object,
                send_devices=target_devices
            )
            
            # Send to logging layer
            await self.logging_callback(middleware_log)
            
        except Exception as e:
            self.logger.error("Error logging middleware event", 
                            error=str(e), 
                            trace_id=event.trace_id)
