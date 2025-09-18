# IoT Data Bridge

외부에서 들어오는 데이터를 **Object**로 매핑하고, 해당 Object의 값을 해당 Object를 보유한 **Device(VM)**에 전달하는 파이썬 기반 미들웨어

## 🏗️ 아키텍처

3개 영역으로 구성된 시스템:

1. **Data Sources**: 외부 데이터 전송
2. **Middleware**: 데이터 매핑 및 전달
3. **Devices**: 데이터 수신 및 처리

## 📁 프로젝트 구조

```
iot-data-bridge/
├── data_sources/            # 외부 데이터 소스
│   ├── test_mqtt_publisher.py
│   ├── test_mqtt_subscriber.py
│   └── test_data.py
├── middleware/              # IoT Data Bridge 미들웨어
│   ├── src/                # 소스 코드
│   ├── config/             # 설정 파일
│   ├── signalr_hub/        # SignalR Hub
│   ├── mosquitto.conf      # MQTT 브로커 설정
│   └── test_full_system.py # 전체 시스템 테스트
├── devices/                 # IoT Device
│   ├── device.py           # Device 실행 파일
│   └── device_config.yaml  # Device 설정 템플릿
└── docs/                   # 문서
    ├── requirements_and_decisions.md
    └── LAYER_DTO_FLOW.md
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 전체 시스템 테스트

```bash
# 미들웨어 디렉토리에서
cd middleware
python test_full_system.py

# 별도 터미널에서 데이터 전송
cd ../data_sources
python test_mqtt_publisher.py
```

### 3. Device 실행

```bash
# 각 VM에서 Device 실행
cd devices
python device.py VM-A
python device.py VM-B
```

## ⚙️ 설정

### MQTT 설정 예시

```yaml
input:
  type: "mqtt"
  mqtt:
    host: "localhost"
    port: 1883
    topic: "iot/ingress"
    qos: 1
```

### SignalR 설정 예시

```yaml
input:
  type: "signalr"
  signalr:
    url: "http://localhost:5000/hub"
    group: "iot_clients"
```

## 📊 데이터 형식

### 입력 데이터 예시

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

### 매핑 규칙 예시

```yaml
mappings:
  - equip_tag: "GPS001"
    message_id: "GLL001"
    object: "Geo.Latitude"
    value_type: float
```

## 📝 로그

### MiddlewareEventLog

```json
{
  "timestamp": "2025-09-18T10:30:45Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "raw": "{...원문 데이터...}",
  "object": "Geo.Latitude",
  "send_devices": ["VM-A", "VM-C"]
}
```

### DeviceIngestLog

```json
{
  "timestamp": "2025-09-18T10:30:46Z",
  "device_id": "VM-A",
  "object": "Geo.Latitude",
  "value": 37.5665
}
```

## 🛠️ 개발

### 테스트 실행

```bash
pytest tests/
```

### 코드 포맷팅

```bash
black src/
isort src/
```

## 📄 라이선스

MIT License

