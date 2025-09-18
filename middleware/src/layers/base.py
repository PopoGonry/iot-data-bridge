"""
Base layer interface and abstract classes
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import asyncio
import structlog

from src.models.events import LayerResult, LayerStatus


class BaseLayer(ABC):
    """Base layer interface"""
    
    def __init__(self, layer_name: str):
        self.layer_name = layer_name
        self.logger = structlog.get_logger(layer_name)
        self.is_running = False
        self.error_count = 0
        self.processed_count = 0
        self.last_activity = None
    
    @abstractmethod
    async def start(self) -> None:
        """Start the layer"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the layer"""
        pass
    
    def get_status(self) -> LayerStatus:
        """Get layer status"""
        return LayerStatus(
            layer_name=self.layer_name,
            is_running=self.is_running,
            last_activity=self.last_activity,
            error_count=self.error_count,
            processed_count=self.processed_count
        )
    
    def _increment_processed(self) -> None:
        """Increment processed count"""
        self.processed_count += 1
        self.last_activity = asyncio.get_event_loop().time()
    
    def _increment_error(self) -> None:
        """Increment error count"""
        self.error_count += 1
        self.last_activity = asyncio.get_event_loop().time()


class InputLayerInterface(BaseLayer):
    """Input layer interface"""
    
    @abstractmethod
    async def process_raw_data(self, raw_data: dict, meta: dict) -> Optional[Any]:
        """Process raw input data"""
        pass


class MappingLayerInterface(BaseLayer):
    """Mapping layer interface"""
    
    @abstractmethod
    async def map_event(self, event: Any) -> Optional[Any]:
        """Map input event to mapped event"""
        pass


class ResolverLayerInterface(BaseLayer):
    """Resolver layer interface"""
    
    @abstractmethod
    async def resolve_event(self, event: Any) -> Optional[Any]:
        """Resolve mapped event to target devices"""
        pass


class TransportsLayerInterface(BaseLayer):
    """Transports layer interface"""
    
    @abstractmethod
    async def send_to_devices(self, event: Any) -> LayerResult:
        """Send event to target devices"""
        pass


class LoggingLayerInterface(BaseLayer):
    """Logging layer interface"""
    
    @abstractmethod
    async def log_middleware_event(self, event: Any) -> None:
        """Log middleware event"""
        pass
    
    @abstractmethod
    async def log_device_ingest(self, event: Any) -> None:
        """Log device ingest event"""
        pass
