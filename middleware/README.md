# Middleware - IoT Data Bridge

외부 데이터를 받아서 Object로 매핑하고 Device에 전달하는 미들웨어입니다.

## 📁 파일 구조

```
middleware/
├── src/                      # 소스 코드
│   ├── main_mqtt.py         # MQTT 전용 메인 애플리케이션
│   ├── main_signalr.py      # SignalR 전용 메인 애플리케이션
│   ├── layers/              # 각 레이어 구현
│   │   ├── input_mqtt.py    # MQTT 전용 입력 처리
│   │   ├── input_signalr.py # SignalR 전용 입력 처리
│   │   ├── transports_mqtt.py    # MQTT 전용 전송 처리
│   │   ├── transports_signalr.py # SignalR 전용 전송 처리
│   │   ├── mapping.py       # 매핑 레이어
│   │   ├── resolver.py      # 리졸버 레이어
│   │   └── logging.py       # 로깅 레이어
│   ├── catalogs/            # 매핑 및 Device 카탈로그
│   ├── models/              # 데이터 모델
│   └── utils/               # 유틸리티
├── config/                  # 설정 파일
│   ├── app-mqtt.yaml       # MQTT 전용 설정
│   ├── app-signalr.yaml    # SignalR 전용 설정
│   ├── mappings.yaml       # 매핑 규칙
│   └── devices.yaml        # Device 정보
├── signalr_hub/            # SignalR Hub 서버
├── mosquitto.conf          # MQTT 브로커 설정
├── mosquitto_data/         # MQTT 데이터 디렉토리
├── logs/                   # 로그 파일
├── start-mqtt.bat          # MQTT Windows 실행 스크립트
├── start-mqtt.sh           # MQTT Linux/macOS 실행 스크립트
├── start-signalr.bat       # SignalR Windows 실행 스크립트
├── start-signalr.sh        # SignalR Linux/macOS 실행 스크립트
├── requirements.txt        # 전체 의존성
├── requirements-mqtt.txt   # MQTT 전용 의존성
├── requirements-signalr.txt # SignalR 전용 의존성
└── test_full_system.py     # 전체 시스템 테스트
```

## 🚀 실행 방법

### **MQTT 버전 실행**
```bash
# Windows
start-mqtt.bat

# Linux/macOS
./start-mqtt.sh

# 또는 직접 실행
python src/main_mqtt.py
```

### **SignalR 버전 실행**
```bash
# Windows
start-signalr.bat

# Linux/macOS
./start-signalr.sh

# 또는 직접 실행
python src/main_signalr.py
```

### **전체 시스템 테스트**
```bash
# MQTT 브로커 + SignalR Hub + IoT Data Bridge 시작
python test_full_system.py
```

### **개별 서비스 실행**
```bash
# MQTT 브로커
mosquitto -c mosquitto.conf

# SignalR Hub
cd signalr_hub && dotnet run

# IoT Data Bridge (MQTT)
python src/main_mqtt.py

# IoT Data Bridge (SignalR)
python src/main_signalr.py
```

## ⚙️ 설정

### **MQTT 설정 (config/app-mqtt.yaml)**
- MQTT Input Layer 설정
- MQTT Transports Layer 설정
- 로깅 설정

### **SignalR 설정 (config/app-signalr.yaml)**
- SignalR Input Layer 설정
- SignalR Transports Layer 설정
- 로깅 설정

### **매핑 규칙 (config/mappings.yaml)**
- (equip_tag, message_id) → object 매핑
- 값 타입 정의

### **Device 정보 (config/devices.yaml)**
- Object → Device 매핑
- Device별 전송 설정

## 🔄 데이터 흐름

1. **외부 데이터 수신** → Input Layer
2. **데이터 매핑** → Mapping Layer
3. **대상 Device 계산** → Resolver Layer
4. **데이터 전송** → Transports Layer
5. **이벤트 로깅** → Logging Layer

## 📝 로그

### **콘솔 로그**
```
Mapping catalog loaded
Device catalog loaded
Starting MQTT transports layer
MQTT transports layer started successfully
Starting logging layer
Logging layer started
MQTT broker started successfully

17:57:41 | INFO | Data sent | device_id=VM-A | object=Geo.Latitude | value=37.4558
17:57:41 | INFO | Data sent | device_id=VM-B | object=Engine1.SpeedRpm | value=4595
```

### **파일 로그**
- **위치**: `logs/iot_data_bridge.log`
- **포맷**: 콘솔 로그와 동일한 `Data sent` 형태
- **내용**: 성공적으로 전달된 데이터만 기록

### **로그 특징**
- ✅ **자동 MQTT 브로커 시작**: middleware 시작 시 자동으로 mosquitto 실행
- ✅ **깔끔한 로그**: `Data sent` 로그만 표시
- ✅ **통일된 포맷**: device와 동일한 로그 포맷 사용
