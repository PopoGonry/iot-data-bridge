# IoT Data Bridge 테스트 가이드

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
# Python 의존성
pip install -r requirements.txt

# MQTT 브로커 (Mosquitto) 설치
# Windows: https://mosquitto.org/download/
# Linux: sudo apt-get install mosquitto mosquitto-clients
# macOS: brew install mosquitto

# .NET 8.0 설치 (SignalR Hub용)
# https://dotnet.microsoft.com/download/dotnet/8.0
```

### 2. 전체 시스템 테스트 (권장)

```bash
# 전체 시스템 시작 (MQTT 브로커 + SignalR Hub + IoT Data Bridge + 모든 Device)
python test_full_system.py

# 별도 터미널에서 테스트 데이터 전송
python test_mqtt_publisher.py
```

### 3. 개별 서비스 테스트

#### 수동으로 서비스 시작
```bash
# 터미널 1: MQTT 브로커
mosquitto -c mosquitto.conf

# 터미널 2: SignalR Hub
cd signalr_hub && dotnet run

# 터미널 3: IoT Data Bridge
python src/main.py

# 터미널 4: 모든 Device
python devices/start_all_devices.py

# 터미널 5: 테스트 데이터 전송
python test_mqtt_publisher.py
```

#### Device 테스트
```bash
# Device ID만 지정 (기본 설정 사용)
python devices/device.py VM-A
python devices/device.py VM-B
python devices/device.py VM-C
python devices/device.py VM-D

# MQTT 호스트/포트 지정
python devices/device.py VM-A localhost 1883
python devices/device.py MyDevice mqtt.example.com 1883

# 설정 파일 사용
python devices/device.py VM-A device_config.yaml

# 새로운 Device 동적 추가
python devices/device.py MyNewDevice
python devices/device.py Sensor-001
python devices/device.py Gateway-02
```

## 📊 테스트 시나리오

### 시나리오 1: GPS 데이터 처리
1. **입력**: GPS 위도/경도 데이터
2. **매핑**: `GPS001` + `GLL001` → `Geo.Latitude`
3. **대상 Device**: `VM-A`, `VM-C`
4. **전송**: MQTT 토픽 `devices/vm-a/ingress`, `devices/vm-c/ingress`

### 시나리오 2: 엔진 데이터 처리
1. **입력**: 엔진 RPM/온도 데이터
2. **매핑**: `ENG001` + `RPM001` → `Engine1.SpeedRpm`
3. **대상 Device**: `VM-B`, `VM-D`
4. **전송**: MQTT 토픽 `devices/vm-b/ingress`, `devices/vm-d/ingress`

### 시나리오 3: 환경 데이터 처리
1. **입력**: 습도/온도 데이터
2. **매핑**: `SENSOR001` + `HUM001` → `Environment.Humidity`
3. **대상 Device**: `VM-C`, `VM-D`
4. **전송**: MQTT 토픽 `devices/vm-c/ingress`, `devices/vm-d/ingress`

## 🔍 로그 확인

### 미들웨어 이벤트 로그
```json
{
  "type": "middleware_event",
  "timestamp": "2025-09-18T10:30:45Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "raw": {},
  "object": "Geo.Latitude",
  "send_devices": ["VM-A", "VM-C"]
}
```

### Device 수신 로그
```json
{
  "type": "device_ingest",
  "timestamp": "2025-09-18T10:30:46Z",
  "device_id": "VM-A",
  "object": "Geo.Latitude",
  "value": 37.5665
}
```

## 🛠️ 문제 해결

### MQTT 연결 실패
```bash
# MQTT 브로커 상태 확인
mosquitto_pub -h localhost -t test -m "hello"
mosquitto_sub -h localhost -t test
```

### SignalR 연결 실패
```bash
# SignalR Hub 상태 확인
curl http://localhost:5000/
```

### 로그 확인
```bash
# 실시간 로그 모니터링
tail -f logs/iot_data_bridge.log
```

## 📁 테스트 파일 구조

```
iot-data-bridge/
├── test_full_system.py         # 전체 시스템 테스트
├── test_mqtt_publisher.py      # MQTT 테스트 데이터 발행
├── test_mqtt_subscriber.py     # MQTT Device 시뮬레이션
├── test_data.py                # 테스트 데이터 생성기
├── mosquitto.conf              # MQTT 브로커 설정
├── signalr_hub/                # SignalR Hub 서버
│   ├── Program.cs
│   └── signalr_hub.csproj
├── devices/                    # Device 구현체들
│   └── device.py               # 통합 Device (모든 VM용)
├── device_config.yaml          # Device 설정 템플릿
└── scripts/
    ├── start.sh / start.bat    # 서비스 시작
    └── stop.sh / stop.bat      # 서비스 중지
```

## 🎯 예상 결과

1. **MQTT 발행자**가 테스트 데이터를 `iot/ingress` 토픽으로 전송
2. **IoT Data Bridge**가 데이터를 수신하고 매핑
3. **대상 Device**가 결정되고 MQTT로 전송
4. **MQTT 구독자**가 Device별 토픽에서 데이터 수신
5. **로그 파일**에 모든 이벤트 기록

이제 전체 시스템을 테스트할 수 있습니다! 🎉
