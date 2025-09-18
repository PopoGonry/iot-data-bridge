"""
Device Catalog - Maps objects to devices and device profiles
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
import structlog

from src.models.events import MappedEvent, ResolvedEvent


class DeviceProfile:
    """Device profile with transport configuration"""
    
    def __init__(self, device_id: str, profile_data: Dict[str, Any]):
        self.device_id = device_id
        self.mqtt = profile_data.get('mqtt')
        self.signalr = profile_data.get('signalr')
    
    def get_transport_config(self, transport_type: str) -> Optional[Dict[str, Any]]:
        """Get transport configuration for specified type"""
        if transport_type == 'mqtt':
            return self.mqtt
        elif transport_type == 'signalr':
            return self.signalr
        return None


class DeviceCatalog:
    """Device catalog manager"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.object_to_devices: Dict[str, List[str]] = {}
        self.device_profiles: Dict[str, DeviceProfile] = {}
        self.logger = structlog.get_logger("device_catalog")
    
    async def load(self):
        """Load device catalog from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Device catalog not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        self.object_to_devices.clear()
        self.device_profiles.clear()
        
        # Load object to devices mapping
        for object_name, device_list in data.get('objects', {}).items():
            self.object_to_devices[object_name] = device_list
            self.logger.debug("Loaded object mapping", 
                            object=object_name, 
                            devices=device_list)
        
        # Load device profiles
        for device_id, profile_data in data.get('devices', {}).items():
            profile = DeviceProfile(device_id, profile_data)
            self.device_profiles[device_id] = profile
            self.logger.debug("Loaded device profile", 
                            device_id=device_id, 
                            has_mqtt=profile.mqtt is not None,
                            has_signalr=profile.signalr is not None)
        
        self.logger.info("Device catalog loaded", 
                        total_objects=len(self.object_to_devices),
                        total_devices=len(self.device_profiles))
    
    def get_devices_for_object(self, object_name: str) -> List[str]:
        """Get list of devices that have the specified object"""
        return self.object_to_devices.get(object_name, [])
    
    def get_device_profile(self, device_id: str) -> Optional[DeviceProfile]:
        """Get device profile for specified device"""
        return self.device_profiles.get(device_id)
    
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
