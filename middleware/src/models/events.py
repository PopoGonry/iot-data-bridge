"""
Event models for IoT Data Bridge - Layer-specific DTOs
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class TransportType(str, Enum):
    """Transport type enumeration"""
    MQTT = "mqtt"
    SIGNALR = "signalr"


class ValueType(str, Enum):
    """Value type enumeration"""
    INT = "int"
    FLOAT = "float"
    STR = "str"
    BOOL = "bool"


# ============================================================================
# INPUT LAYER DTOs
# ============================================================================

class IngressEvent(BaseModel):
    """Input Layer Output DTO - Raw input event with metadata"""
    trace_id: str = Field(..., description="Unique trace identifier")
    raw: Dict[str, Any] = Field(..., description="Raw input data")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# MAPPING LAYER DTOs
# ============================================================================

class MappingRule(BaseModel):
    """Mapping rule DTO"""
    equip_tag: str = Field(..., description="Equipment tag")
    message_id: str = Field(..., description="Message ID")
    object: str = Field(..., description="Target object name")
    value_type: ValueType = Field(..., description="Value type")
    
    def get_key(self) -> tuple[str, str]:
        """Get mapping key"""
        return (self.equip_tag, self.message_id)


class MappedEvent(BaseModel):
    """Mapping Layer Output DTO - Mapped event with object and value"""
    trace_id: str = Field(..., description="Unique trace identifier")
    object: str = Field(..., description="Mapped object name")
    value: Any = Field(..., description="Mapped value")
    value_type: ValueType = Field(..., description="Value type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# RESOLVER LAYER DTOs
# ============================================================================

class ResolvedEvent(BaseModel):
    """Resolver Layer Output DTO - Resolved event with target devices"""
    trace_id: str = Field(..., description="Unique trace identifier")
    object: str = Field(..., description="Object name")
    value: Any = Field(..., description="Value")
    target_devices: List[str] = Field(..., description="Target device IDs")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# TRANSPORTS LAYER DTOs
# ============================================================================

class TransportConfig(BaseModel):
    """Transport configuration DTO"""
    type: TransportType = Field(..., description="Transport type")
    config: Dict[str, Any] = Field(..., description="Transport-specific configuration")


class DeviceTarget(BaseModel):
    """Device target DTO for transport"""
    device_id: str = Field(..., description="Device ID")
    transport_config: TransportConfig = Field(..., description="Transport configuration")
    object: str = Field(..., description="Object name")
    value: Any = Field(..., description="Value to send")


class TransportEvent(BaseModel):
    """Transports Layer Input DTO - Event to be transported"""
    trace_id: str = Field(..., description="Unique trace identifier")
    device_targets: List[DeviceTarget] = Field(..., description="Device targets")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# LOGGING LAYER DTOs
# ============================================================================

class MiddlewareEventLog(BaseModel):
    """Middleware event log entry"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str = Field(..., description="Trace ID")
    raw: Dict[str, Any] = Field(..., description="Raw input data")
    object: str = Field(..., description="Object name")
    send_devices: List[str] = Field(..., description="Target devices")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeviceIngestLog(BaseModel):
    """Device ingest log entry"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str = Field(..., description="Trace ID")
    device_id: str = Field(..., description="Device ID")
    object: str = Field(..., description="Object name")
    value: Any = Field(..., description="Value")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# LAYER INTERFACE DTOs
# ============================================================================

class LayerResult(BaseModel):
    """Generic layer result DTO"""
    success: bool = Field(..., description="Operation success status")
    data: Optional[Any] = Field(default=None, description="Result data")
    error: Optional[str] = Field(default=None, description="Error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Result timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LayerStatus(BaseModel):
    """Layer status DTO"""
    layer_name: str = Field(..., description="Layer name")
    is_running: bool = Field(..., description="Running status")
    last_activity: Optional[datetime] = Field(default=None, description="Last activity timestamp")
    error_count: int = Field(default=0, description="Error count")
    processed_count: int = Field(default=0, description="Processed message count")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }