#!/usr/bin/env python3
"""
Test data generator for IoT Data Bridge - Marine Equipment Data Generator
Based on NMEA and marine equipment specifications
"""

import json
import uuid
import random
from datetime import datetime


def generate_random_test_data():
    """Generate random test data for all marine equipment objects"""
    
    # 모든 해양 장비 오브젝트에 대한 랜덤 데이터 생성
    test_cases = [
        # GPS Navigation Data
        {
            "name": "GPS Latitude",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "GPS-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "GPSDATA"
                },
                "payload": {
                    "Equip.Tag": "GPS001",
                    "Message.ID": "GLL001",
                    "VALUE": round(random.uniform(37.0, 38.0), 4)  # 서울 근처 위도 범위
                }
            }
        },
        {
            "name": "GPS Longitude",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "GPS-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "GPSDATA"
                },
                "payload": {
                    "Equip.Tag": "GPS001",
                    "Message.ID": "GLL002",
                    "VALUE": round(random.uniform(126.0, 127.0), 4)  # 서울 근처 경도 범위
                }
            }
        },
        {
            "name": "GPS Course Over Ground",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "GPS-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "GPSDATA"
                },
                "payload": {
                    "Equip.Tag": "GPS001",
                    "Message.ID": "VTG001",
                    "VALUE": round(random.uniform(0.0, 360.0), 1)  # COG 0-360도
                }
            }
        },
        {
            "name": "GPS Speed Over Ground",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "GPS-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "GPSDATA"
                },
                "payload": {
                    "Equip.Tag": "GPS001",
                    "Message.ID": "VTG002",
                    "VALUE": round(random.uniform(0.0, 30.0), 1)  # SOG 0-30 knot
                }
            }
        },

        # Speed Log Data
        {
            "name": "Speed Through Water",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "LOG-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "LOGDATA"
                },
                "payload": {
                    "Equip.Tag": "LOG001",
                    "Message.ID": "VHW003",
                    "VALUE": round(random.uniform(0.0, 25.0), 1)  # STW 0-25 knot
                }
            }
        },

        # Wind Data
        {
            "name": "Wind Angle",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "WIND-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "WINDDATA"
                },
                "payload": {
                    "Equip.Tag": "WIND001",
                    "Message.ID": "MWV101",
                    "VALUE": round(random.uniform(0.0, 360.0), 1)  # Wind Angle 0-360도
                }
            }
        },
        {
            "name": "Wind Reference",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "WIND-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "WINDDATA"
                },
                "payload": {
                    "Equip.Tag": "WIND001",
                    "Message.ID": "MWV102",
                    "VALUE": random.choice(["T", "R"])  # T=Theoretical, R=Relative
                }
            }
        },
        {
            "name": "Wind Speed",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "WIND-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "WINDDATA"
                },
                "payload": {
                    "Equip.Tag": "WIND001",
                    "Message.ID": "MWV103",
                    "VALUE": round(random.uniform(0.0, 50.0), 1)  # Wind Speed 0-50
                }
            }
        },
        {
            "name": "Wind Speed Unit",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "WIND-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "WINDDATA"
                },
                "payload": {
                    "Equip.Tag": "WIND001",
                    "Message.ID": "MWV104",
                    "VALUE": random.choice(["K", "M", "N"])  # K=km/h, M=m/s, N=knot
                }
            }
        },

        # Echo Sounder Data
        {
            "name": "Water Depth",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ES-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ESDATA"
                },
                "payload": {
                    "Equip.Tag": "ES001",
                    "Message.ID": "DPT101",
                    "VALUE": round(random.uniform(1.0, 200.0), 1)  # Water Depth 1-200m
                }
            }
        },
        {
            "name": "Water Temperature",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ES-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ESDATA"
                },
                "payload": {
                    "Equip.Tag": "ES001",
                    "Message.ID": "MTW001",
                    "VALUE": round(random.uniform(-2.0, 35.0), 1)  # Water Temperature -2~35°C
                }
            }
        },

        # Engine 1 Data
        {
            "name": "Engine 1 Data Source",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG001",
                    "Message.ID": "RPM001",
                    "VALUE": random.choice(["E", "S", "P"])  # E=Engine, S=Shaft, P=Propeller
                }
            }
        },
        {
            "name": "Engine 1 Shaft Number",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG001",
                    "Message.ID": "RPM002",
                    "VALUE": random.randint(0, 4)  # Shaft Number 0-4
                }
            }
        },
        {
            "name": "Engine 1 Speed",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG001",
                    "Message.ID": "RPM003",
                    "VALUE": round(random.uniform(100.0, 2000.0), 1)  # Engine Speed 100-2000 RPM
                }
            }
        },
        {
            "name": "Engine 1 Propeller Pitch",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG001",
                    "Message.ID": "RPM004",
                    "VALUE": round(random.uniform(-100.0, 100.0), 1)  # Propeller Pitch -100~100%
                }
            }
        },
        {
            "name": "Engine 1 Status",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG001",
                    "Message.ID": "RPM005",
                    "VALUE": random.choice(["A", "V"])  # A=Valid, V=Invalid
                }
            }
        },

        # Engine 2 Data
        {
            "name": "Engine 2 Data Source",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-02",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG002",
                    "Message.ID": "RPM006",
                    "VALUE": random.choice(["E", "S", "P"])  # E=Engine, S=Shaft, P=Propeller
                }
            }
        },
        {
            "name": "Engine 2 Shaft Number",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-02",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG002",
                    "Message.ID": "RPM007",
                    "VALUE": random.randint(0, 4)  # Shaft Number 0-4
                }
            }
        },
        {
            "name": "Engine 2 Speed",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-02",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG002",
                    "Message.ID": "RPM008",
                    "VALUE": round(random.uniform(100.0, 2000.0), 1)  # Engine Speed 100-2000 RPM
                }
            }
        },
        {
            "name": "Engine 2 Propeller Pitch",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-02",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG002",
                    "Message.ID": "RPM009",
                    "VALUE": round(random.uniform(-100.0, 100.0), 1)  # Propeller Pitch -100~100%
                }
            }
        },
        {
            "name": "Engine 2 Status",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "ENG-GW-02",
                    "DEST": "IoTDataBridge",
                    "TYPE": "ENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "ENG002",
                    "Message.ID": "RPM010",
                    "VALUE": random.choice(["A", "V"])  # A=Valid, V=Invalid
                }
            }
        },

        # Rudder Data
        {
            "name": "Starboard Rudder Angle",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "RUD-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "RUDDERDATA"
                },
                "payload": {
                    "Equip.Tag": "RUD001",
                    "Message.ID": "RSA001",
                    "VALUE": round(random.uniform(-35.0, 35.0), 1)  # Rudder Angle -35~35도
                }
            }
        },
        {
            "name": "Starboard Rudder Status",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "RUD-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "RUDDERDATA"
                },
                "payload": {
                    "Equip.Tag": "RUD001",
                    "Message.ID": "RSA002",
                    "VALUE": random.choice(["A", "V"])  # A=Valid, V=Invalid
                }
            }
        },
        {
            "name": "Port Rudder Angle",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "RUD-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "RUDDERDATA"
                },
                "payload": {
                    "Equip.Tag": "RUD001",
                    "Message.ID": "RSA003",
                    "VALUE": round(random.uniform(-35.0, 35.0), 1)  # Rudder Angle -35~35도
                }
            }
        },
        {
            "name": "Port Rudder Status",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "RUD-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "RUDDERDATA"
                },
                "payload": {
                    "Equip.Tag": "RUD001",
                    "Message.ID": "RSA004",
                    "VALUE": random.choice(["A", "V"])  # A=Valid, V=Invalid
                }
            }
        },

        # VDR Data
        {
            "name": "Current Set",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "VDR-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "VDRDATA"
                },
                "payload": {
                    "Equip.Tag": "VDR001",
                    "Message.ID": "VDR001",
                    "VALUE": round(random.uniform(0.0, 360.0), 1)  # Current Set 0-360도
                }
            }
        },
        {
            "name": "Current Drift",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "VDR-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "VDRDATA"
                },
                "payload": {
                    "Equip.Tag": "VDR001",
                    "Message.ID": "VDR002",
                    "VALUE": round(random.uniform(0.0, 5.0), 1)  # Current Drift 0-5 knot
                }
            }
        },

        # Inclinometer Data
        {
            "name": "Roll Angle",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "CLI-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "INCLINOMETERDATA"
                },
                "payload": {
                    "Equip.Tag": "CLI001",
                    "Message.ID": "XDR001",
                    "VALUE": round(random.uniform(-30.0, 30.0), 1)  # Roll -30~30도
                }
            }
        },
        {
            "name": "Pitch Angle",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "CLI-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "INCLINOMETERDATA"
                },
                "payload": {
                    "Equip.Tag": "CLI001",
                    "Message.ID": "XDR002",
                    "VALUE": round(random.uniform(-15.0, 15.0), 1)  # Pitch -15~15도
                }
            }
        },

        # Gyrocompass Data
        {
            "name": "Magnetic Heading",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "GYRO-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "GYRODATA"
                },
                "payload": {
                    "Equip.Tag": "GYRO001",
                    "Message.ID": "HDG001",
                    "VALUE": round(random.uniform(0.0, 360.0), 1)  # Magnetic Heading 0-360도
                }
            }
        },
        {
            "name": "True Heading",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "GYRO-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "GYRODATA"
                },
                "payload": {
                    "Equip.Tag": "GYRO001",
                    "Message.ID": "THS001",
                    "VALUE": round(random.uniform(0.0, 360.0), 1)  # True Heading 0-360도
                }
            }
        },

        # Diesel Engine 1 Data (Sample of key parameters)
        {
            "name": "Diesel Engine 1 RPM",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "DE-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "DIESELENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "DE001",
                    "Message.ID": "RPM",
                    "VALUE": round(random.uniform(500.0, 2000.0), 1)  # Diesel Engine RPM 500-2000
                }
            }
        },
        {
            "name": "Diesel Engine 1 Load",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "DE-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "DIESELENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "DE001",
                    "Message.ID": "Load",
                    "VALUE": round(random.uniform(0.0, 100.0), 1)  # Engine Load 0-100%
                }
            }
        },
        {
            "name": "Diesel Engine 1 Power",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "DE-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "DIESELENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "DE001",
                    "Message.ID": "Power",
                    "VALUE": round(random.uniform(0.0, 5000.0), 1)  # Engine Power 0-5000 KW
                }
            }
        },

        # Gas Engine 1 Data
        {
            "name": "Gas Engine 1 RPM",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "GE-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "GASENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "GE001",
                    "Message.ID": "RPM",
                    "VALUE": round(random.uniform(1000.0, 3000.0), 1)  # Gas Engine RPM 1000-3000
                }
            }
        },
        {
            "name": "Gas Engine 1 Exhaust Gas Inlet Temperature",
            "data": {
                "header": {
                    "UUID": str(uuid.uuid4()),
                    "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "SRC": "GE-GW-01",
                    "DEST": "IoTDataBridge",
                    "TYPE": "GASENGINEDATA"
                },
                "payload": {
                    "Equip.Tag": "GE001",
                    "Message.ID": "ExhGasInletTempA",
                    "VALUE": round(random.uniform(200.0, 600.0), 1)  # Exhaust Gas Inlet Temp 200-600°C
                }
            }
        }
    ]
    
    return test_cases


def generate_test_data():
    """Legacy function for backward compatibility"""
    return generate_random_test_data()


def print_test_data():
    """Print test data in JSON format"""
    test_cases = generate_test_data()
    
    print("=== IoT Data Bridge Marine Equipment Test Data ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}")
        print(json.dumps(test_case['data'], indent=2, ensure_ascii=False))
        print()


if __name__ == "__main__":
    print_test_data()
