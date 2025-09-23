"""
Mapping Catalog - Maps (equip_tag, message_id) to object and value_type
"""

import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple
import structlog

from models.events import IngressEvent, MappedEvent


class MappingRule:
    """Single mapping rule"""
    
    def __init__(self, equip_tag: str, message_id: str, object: str, value_type: str):
        self.equip_tag = equip_tag
        self.message_id = message_id
        self.object = object
        self.value_type = value_type
    
    def __repr__(self):
        return f"MappingRule({self.equip_tag}, {self.message_id} -> {self.object}:{self.value_type})"


class MappingCatalog:
    """Mapping catalog manager"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.mappings: Dict[Tuple[str, str], MappingRule] = {}
        self.logger = structlog.get_logger("mapping_catalog")
    
    async def load(self):
        """Load mapping rules from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Mapping catalog not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        self.mappings.clear()
        
        for mapping_data in data.get('mappings', []):
            rule = MappingRule(
                equip_tag=mapping_data['equip_tag'],
                message_id=mapping_data['message_id'],
                object=mapping_data['object'],
                value_type=mapping_data['value_type']
            )
            
            key = (rule.equip_tag, rule.message_id)
            self.mappings[key] = rule
            
            self.logger.debug("Loaded mapping rule", 
                            equip_tag=rule.equip_tag,
                            message_id=rule.message_id,
                            object=rule.object,
                            value_type=rule.value_type)
        
        self.logger.info("Mapping catalog loaded", total_rules=len(self.mappings))
    
    def get_mapping(self, equip_tag: str, message_id: str) -> Optional[MappingRule]:
        """Get mapping rule for equip_tag and message_id"""
        key = (equip_tag, message_id)
        return self.mappings.get(key)
    
    def map_event(self, event: IngressEvent) -> Optional[MappedEvent]:
        """Map ingress event to mapped event"""
        try:
            # Extract equip_tag and message_id from payload
            payload = event.raw.get('payload', {})
            equip_tag = payload.get('Equip.Tag')
            message_id = payload.get('Message.ID')
            value = payload.get('VALUE')
            
            if not all([equip_tag, message_id, value is not None]):
                self.logger.warning("Missing required fields in payload",
                                  equip_tag=equip_tag,
                                  message_id=message_id,
                                  has_value=value is not None)
                return None
            
            # Get mapping rule
            rule = self.get_mapping(equip_tag, message_id)
            if not rule:
                self.logger.warning("No mapping rule found",
                                  equip_tag=equip_tag,
                                  message_id=message_id)
                return None
            
            # Cast value to specified type
            casted_value = self._cast_value(value, rule.value_type)
            if casted_value is None:
                self.logger.error("Failed to cast value",
                                value=value,
                                value_type=rule.value_type,
                                equip_tag=equip_tag,
                                message_id=message_id)
                return None
            
            return MappedEvent(
                trace_id=event.trace_id,
                object=rule.object,
                value=casted_value,
                value_type=rule.value_type
            )
            
        except Exception as e:
            self.logger.error("Error mapping event", error=str(e), trace_id=event.trace_id)
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
