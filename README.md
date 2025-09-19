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
├── data-sources/            # 외부 데이터 소스 (독립 프로젝트)
│   ├── mqtt_publisher.py           # MQTT 데이터 발행기
│   ├── data_generator.py           # 외부 데이터 생성기
│   ├── start.bat                   # Windows 실행 스크립트
│   ├── start.sh                    # Linux/macOS 실행 스크립트
│   ├── requirements.txt            # 프로젝트 의존성
│   └── README.md                   # 사용법 문서
├── middleware/              # IoT Data Bridge 미들웨어 (독립 프로젝트)
│   ├── src/                # 소스 코드
│   │   ├── main_mqtt.py           # MQTT 전용 메인
│   │   ├── main_signalr.py        # SignalR 전용 메인
│   │   └── layers/                # 레이어 구현
│   ├── config/             # 설정 파일
│   │   ├── app-mqtt.yaml          # MQTT 전용 설정
│   │   ├── app-signalr.yaml       # SignalR 전용 설정
│   │   ├── devices.yaml           # 디바이스 매핑
│   │   └── mappings.yaml          # 데이터 매핑
│   ├── signalr_hub/        # SignalR Hub
│   ├── mosquitto.conf      # MQTT 브로커 설정
│   ├── start-mqtt.bat      # MQTT Windows 실행 스크립트
│   ├── start-mqtt.sh       # MQTT Linux/macOS 실행 스크립트
│   ├── start-signalr.bat   # SignalR Windows 실행 스크립트
│   ├── start-signalr.sh    # SignalR Linux/macOS 실행 스크립트
│   ├── test_config.py      # 설정 테스트
│   ├── test_full_system.py # 전체 시스템 테스트
│   ├── requirements.txt    # 전체 의존성
│   ├── requirements-mqtt.txt    # MQTT 전용 의존성
│   ├── requirements-signalr.txt # SignalR 전용 의존성
│   └── README.md           # 사용법 문서
├── devices/                 # IoT Device (독립 프로젝트)
│   ├── device.py           # Device 실행 파일 (명령행 인수 사용)
│   ├── start.bat           # Windows 실행 스크립트
│   ├── start.sh            # Linux/macOS 실행 스크립트
│   ├── requirements.txt    # 프로젝트 의존성
│   └── README.md           # 사용법 문서
└── docs/                   # 프로젝트 문서
    ├── requirements_and_decisions.md
    └── LAYER_DTO_FLOW.md
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
# 각 프로젝트별로 의존성 설치
cd data-sources && pip install -r requirements.txt
cd ../middleware && pip install -r requirements.txt  
cd ../devices && pip install -r requirements.txt
```

### 2. 간편 실행

```bash
# Data Sources
cd data-sources && start.bat    # Windows
cd data-sources && ./start.sh   # Linux/macOS

# Middleware - MQTT 버전
cd middleware && start-mqtt.bat      # Windows  
cd middleware && ./start-mqtt.sh     # Linux/macOS

# Middleware - SignalR 버전
cd middleware && start-signalr.bat   # Windows
cd middleware && ./start-signalr.sh  # Linux/macOS

# Devices
cd devices && start.bat         # Windows
cd devices && ./start.sh        # Linux/macOS
```

### 3. 설정 파일 수정 (필요시)

```bash
# 미들웨어 설정 (필요시 IP 주소 수정)
# middleware/config/app-mqtt.yaml 파일에서 MQTT IP 주소 수정
# middleware/config/app-signalr.yaml 파일에서 SignalR IP 주소 수정

# 디바이스는 명령행 인수로 설정 (설정 파일 불필요)
```

### 4. 전체 시스템 테스트

```bash
# 미들웨어 디렉토리에서
cd middleware
python test_full_system.py

# 별도 터미널에서 데이터 전송 (5초마다 랜덤 데이터)
cd ../data-sources
python mqtt_publisher.py localhost 1883
```

### 5. Device 실행

```bash
# 각 VM에서 Device 실행 (명령행 인수 사용)
cd devices
python device.py VM-A localhost 1883
python device.py VM-B 192.168.1.100 1883

# 또는 start.sh 스크립트 사용
./start.sh  # 대화형으로 device_id, host, port 입력
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

### 통일된 로그 포맷

**Middleware (Data sent):**
```
2025-09-19 17:57:41 | INFO | Data sent | device_id=VM-A | object=Geo.Latitude | value=37.4558
2025-09-19 17:57:41 | INFO | Data sent | device_id=VM-B | object=Engine1.SpeedRpm | value=4595
```

**Device (Data received):**
```
2025-09-19 17:57:41 | INFO | Data received | device_id=VM-A | object=Geo.Latitude | value=37.4558
2025-09-19 17:57:41 | INFO | Data received | device_id=VM-B | object=Engine1.SpeedRpm | value=4595
```

### 로그 파일 위치

- **Middleware**: `middleware/logs/iot_data_bridge.log`
- **Device**: `devices/logs/device.log`

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

