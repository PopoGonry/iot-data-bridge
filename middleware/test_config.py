#!/usr/bin/env python3
"""
Configuration Test Script
"""

import sys
import yaml
from pathlib import Path

def test_config_files():
    """Test configuration files"""
    print("Testing configuration files...")
    
    # Test app.yaml
    try:
        with open("config/app.yaml", 'r', encoding='utf-8') as f:
            app_config = yaml.safe_load(f)
        print("✓ app.yaml loaded successfully")
        print(f"  - App name: {app_config.get('app_name')}")
        print(f"  - Mapping catalog: {app_config.get('mapping_catalog_path')}")
        print(f"  - Device catalog: {app_config.get('device_catalog_path')}")
    except Exception as e:
        print(f"✗ app.yaml error: {e}")
        return False
    
    # Test mappings.yaml
    try:
        with open("config/mappings.yaml", 'r', encoding='utf-8') as f:
            mappings = yaml.safe_load(f)
        print("✓ mappings.yaml loaded successfully")
        print(f"  - Number of mappings: {len(mappings.get('mappings', []))}")
    except Exception as e:
        print(f"✗ mappings.yaml error: {e}")
        return False
    
    # Test devices.yaml
    try:
        with open("config/devices.yaml", 'r', encoding='utf-8') as f:
            devices = yaml.safe_load(f)
        print("✓ devices.yaml loaded successfully")
        print(f"  - Number of objects: {len(devices.get('objects', {}))}")
        print(f"  - Number of devices: {len(devices.get('devices', {}))}")
    except Exception as e:
        print(f"✗ devices.yaml error: {e}")
        return False
    
    return True

def test_imports():
    """Test Python imports"""
    print("\nTesting Python imports...")
    
    try:
        from src.models.config import AppConfig
        print("✓ AppConfig imported successfully")
    except Exception as e:
        print(f"✗ AppConfig import error: {e}")
        return False
    
    try:
        from src.models.events import IngressEvent, MappedEvent, ResolvedEvent
        print("✓ Event models imported successfully")
    except Exception as e:
        print(f"✗ Event models import error: {e}")
        return False
    
    try:
        from src.layers.input import InputLayer
        print("✓ InputLayer imported successfully")
    except Exception as e:
        print(f"✗ InputLayer import error: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("IoT Data Bridge Configuration Test")
    print("=" * 40)
    
    # Change to middleware directory
    middleware_dir = Path(__file__).parent
    import os
    os.chdir(middleware_dir)
    
    # Test configuration files
    config_ok = test_config_files()
    
    # Test imports
    import_ok = test_imports()
    
    print("\n" + "=" * 40)
    if config_ok and import_ok:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
