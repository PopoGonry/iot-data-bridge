# Data Sources - 외부 데이터 소스

외부에서 IoT Data Bridge로 데이터를 전송하는 부분입니다.

## 📁 파일 구조

```
data_sources/
├── test_mqtt_publisher.py    # MQTT 테스트 데이터 발행
├── test_mqtt_subscriber.py   # MQTT 구독자 (Device 시뮬레이션)
└── test_data.py              # 테스트 데이터 생성기
```

## 🚀 사용 방법

### **테스트 데이터 발행**
```bash
# MQTT로 테스트 데이터 전송
python test_mqtt_publisher.py
```

### **Device 시뮬레이션**
```bash
# MQTT 구독자로 Device 시뮬레이션
python test_mqtt_subscriber.py
```

### **테스트 데이터 생성**
```bash
# 테스트 데이터 예시 출력
python test_data.py
```

## 📊 전송되는 데이터 형식

```json
{
  "header": {
    "UUID": "550e8400-e29b-41d4-a716-446655440000",
    "TIME": "20250918103045",
    "SRC": "SENSOR-GW-01",
    "DEST": "IoTDataBridge",
    "TYPE": "SENSORDATA"
  },
  "payload": {
    "Equip.Tag": "GPS001",
    "Message.ID": "GLL001",
    "VALUE": 37.5665
  }
}
```

## 🎯 테스트 시나리오

1. **GPS 데이터**: 위도/경도/고도
2. **엔진 데이터**: RPM/온도
3. **환경 데이터**: 습도/온도
