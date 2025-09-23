"""
Device Catalog - Maps objects to devices and device profiles
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
import structlog

from models.events import MappedEvent, ResolvedEvent


class DeviceCatalog:
    """Device catalog manager"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.object_to_devices: Dict[str, List[str]] = {}
        self.logger = structlog.get_logger("device_catalog")
    
    async def load(self):
        """Load device catalog from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Device catalog not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        self.object_to_devices.clear()
        
        # Load object to devices mapping
        for object_name, device_list in data.get('objects', {}).items():
            self.object_to_devices[object_name] = device_list
            self.logger.debug("Loaded object mapping", 
                            object=object_name, 
                            devices=device_list)
        
        # Device profiles no longer needed - devices handle their own configuration
        
        self.logger.info("Device catalog loaded", 
                        total_objects=len(self.object_to_devices))
    
    def get_devices_for_object(self, object_name: str) -> List[str]:
        """Get list of devices that have the specified object"""
        return self.object_to_devices.get(object_name, [])
    
    # Device profiles no longer needed
    
    def resolve_event(self, event: MappedEvent) -> ResolvedEvent:
        """Resolve mapped event to target devices"""
        target_devices = self.get_devices_for_object(event.object)
        
        self.logger.debug("Resolved event", 
                        trace_id=event.trace_id,
                        object=event.object,
                        target_devices=target_devices)
        
        return ResolvedEvent(
            trace_id=event.trace_id,
            object=event.object,
            value=event.value,
            target_devices=target_devices
        )
