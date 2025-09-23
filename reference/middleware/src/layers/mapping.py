"""
Mapping Layer - Maps input data to objects using mapping catalog
"""

import asyncio
from typing import Optional, Callable
import structlog

from layers.base import MappingLayerInterface
from models.events import IngressEvent, MappedEvent, ValueType
from catalogs.mapping_catalog import MappingCatalog


class MappingLayer(MappingLayerInterface):
    """Mapping Layer - Transforms IngressEvent to MappedEvent"""
    
    def __init__(self, mapping_catalog: MappingCatalog, resolver_callback: Callable[[MappedEvent], None]):
        super().__init__("mapping_layer")
        self.mapping_catalog = mapping_catalog
        self.resolver_callback = resolver_callback
    
    async def start(self):
        """Start mapping layer"""
        self.is_running = True
    
    async def stop(self):
        """Stop mapping layer"""
        self.is_running = False
    
    async def map_event(self, event: IngressEvent) -> Optional[MappedEvent]:
        """Map ingress event to mapped event"""
        try:
            self._increment_processed()
            
            # Extract payload data
            payload = event.raw.get('payload', {})
            equip_tag = payload.get('Equip.Tag')
            message_id = payload.get('Message.ID')
            value = payload.get('VALUE')
            
            # Validate required fields
            if not all([equip_tag, message_id, value is not None]):
                self._increment_error()
                return None
            
            # Get mapping rule
            rule = self.mapping_catalog.get_mapping(equip_tag, message_id)
            if not rule:
                self._increment_error()
                return None
            
            casted_value = self._cast_value(value, rule.value_type)
            if casted_value is None:
                self._increment_error()
                return None
            
            # Create mapped event
            mapped_event = MappedEvent(
                trace_id=event.trace_id,
                object=rule.object,
                value=casted_value,
                value_type=ValueType(rule.value_type)
            )
            
            # Forward to resolver layer
            await self.resolver_callback(mapped_event)
            
            return mapped_event
            
        except Exception as e:
            self.logger.error("Error in map_event", error=str(e))
            import traceback
            self.logger.error("Traceback", traceback=traceback.format_exc())
            self._increment_error()
            return None
    
    def _cast_value(self, value: any, value_type: str) -> any:
        """Cast value to specified type"""
        try:
            if value_type == 'integer':
                return int(value)
            elif value_type == 'float':
                return float(value)
            elif value_type == 'text':
                return str(value)
            elif value_type == 'boolean':
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            else:
                return value
        except (ValueError, TypeError) as e:
            return None