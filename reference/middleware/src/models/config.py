"""
Configuration models for IoT Data Bridge
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Log level")
    file: str = Field(default="logs/iot_data_bridge.log", description="Log file path")
    max_size: int = Field(default=10 * 1024 * 1024, description="Max log file size in bytes")
    backup_count: int = Field(default=5, description="Number of backup files")


class MQTTConfig(BaseModel):
    """MQTT configuration"""
    host: str = Field(..., description="MQTT broker host")
    port: int = Field(default=1883, description="MQTT broker port")
    username: Optional[str] = Field(default=None, description="MQTT username")
    password: Optional[str] = Field(default=None, description="MQTT password")
    topic: str = Field(..., description="MQTT topic to subscribe")
    qos: int = Field(default=1, description="MQTT QoS level")
    keepalive: int = Field(default=60, description="MQTT keepalive interval")
    ssl: bool = Field(default=False, description="Use SSL/TLS")


class SignalRConfig(BaseModel):
    """SignalR configuration"""
    url: str = Field(..., description="SignalR hub URL")
    group: str = Field(..., description="SignalR group name")
    username: Optional[str] = Field(default=None, description="SignalR username")
    password: Optional[str] = Field(default=None, description="SignalR password")


class InputConfig(BaseModel):
    """Input layer configuration"""
    type: str = Field(..., description="Input type: mqtt or signalr")
    mqtt: Optional[MQTTConfig] = Field(default=None, description="MQTT configuration")
    signalr: Optional[SignalRConfig] = Field(default=None, description="SignalR configuration")


class TransportsConfig(BaseModel):
    """Transports layer configuration"""
    type: str = Field(..., description="Transport type: mqtt or signalr")
    mqtt: Optional[MQTTConfig] = Field(default=None, description="MQTT configuration")
    signalr: Optional[SignalRConfig] = Field(default=None, description="SignalR configuration")


class AppConfig(BaseModel):
    """Main application configuration"""
    app_name: str = Field(default="IoT Data Bridge", description="Application name")
    mapping_catalog_path: str = Field(default="config/mappings.yaml", description="Mapping catalog path")
    device_catalog_path: str = Field(default="config/devices.yaml", description="Device catalog path")
    
    input: InputConfig = Field(..., description="Input layer configuration")
    transports: TransportsConfig = Field(..., description="Transports layer configuration")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")