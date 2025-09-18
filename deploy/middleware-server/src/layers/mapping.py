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
        self.logger.info("Starting mapping layer")
        self.is_running = True
        self.logger.info("Mapping layer started")
    
    async def stop(self):
        """Stop mapping layer"""
        self.logger.info("Stopping mapping layer")
        self.is_running = False
        self.logger.info("Mapping layer stopped")
    
    async def map_event(self, event: IngressEvent) -> Optional[MappedEvent]:
        """Map ingress event to mapped event"""
        try:
            self._increment_processed()
            
            self.logger.debug("Mapping event", trace_id=event.trace_id)
            
            # Extract payload data
            payload = event.raw.get('payload', {})
            equip_tag = payload.get('Equip.Tag')
            message_id = payload.get('Message.ID')
            value = payload.get('VALUE')
            
            # Validate required fields
            if not all([equip_tag, message_id, value is not None]):
                self.logger.warning("Missing required fields in payload",
                                  trace_id=event.trace_id,
                                  equip_tag=equip_tag,
                                  message_id=message_id,
                                  has_value=value is not None)
                self._increment_error()
                return None
            
            # Get mapping rule
            rule = self.mapping_catalog.get_mapping(equip_tag, message_id)
            if not rule:
                self.logger.warning("No mapping rule found",
                                  trace_id=event.trace_id,
                                  equip_tag=equip_tag,
                                  message_id=message_id)
                self._increment_error()
                return None
            
            # Cast value to specified type
            casted_value = self._cast_value(value, rule.value_type)
            if casted_value is None:
                self.logger.error("Failed to cast value",
                                trace_id=event.trace_id,
                                value=value,
                                value_type=rule.value_type,
                                equip_tag=equip_tag,
                                message_id=message_id)
                self._increment_error()
                return None
            
            # Create mapped event
            mapped_event = MappedEvent(
                trace_id=event.trace_id,
                object=rule.object,
                value=casted_value,
                value_type=ValueType(rule.value_type)
            )
            
            self.logger.debug("Successfully mapped event",
                            trace_id=event.trace_id,
                            object=rule.object,
                            value=casted_value,
                            value_type=rule.value_type)
            
            # Forward to resolver layer
            await self.resolver_callback(mapped_event)
            
            return mapped_event
            
        except Exception as e:
            self._increment_error()
            self.logger.error("Error mapping event", 
                            error=str(e), 
                            trace_id=event.trace_id)
            return None
    
    def _cast_value(self, value: any, value_type: str) -> any:
        """Cast value to specified type"""
        try:
            if value_type == 'int':
                return int(value)
            elif value_type == 'float':
                return float(value)
            elif value_type == 'str':
                return str(value)
            elif value_type == 'bool':
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            else:
                self.logger.warning("Unknown value type", value_type=value_type)
                return value
        except (ValueError, TypeError) as e:
            self.logger.error("Value casting failed", 
                            value=value, 
                            value_type=value_type, 
                            error=str(e))
            return None
