# Middleware - IoT Data Bridge

외부 데이터를 받아서 Object로 매핑하고 Device에 전달하는 미들웨어입니다.

## 📁 파일 구조

```
middleware/
├── src/                      # 소스 코드
│   ├── main.py              # 메인 애플리케이션
│   ├── layers/              # 각 레이어 구현
│   ├── catalogs/            # 매핑 및 Device 카탈로그
│   ├── models/              # 데이터 모델
│   └── utils/               # 유틸리티
├── config/                  # 설정 파일
│   ├── app.yaml            # 메인 설정
│   ├── mappings.yaml       # 매핑 규칙
│   └── devices.yaml        # Device 정보
├── signalr_hub/            # SignalR Hub 서버
├── mosquitto.conf          # MQTT 브로커 설정
├── mosquitto_data/         # MQTT 데이터 디렉토리
├── logs/                   # 로그 파일
└── test_full_system.py     # 전체 시스템 테스트
```

## 🚀 실행 방법

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

# IoT Data Bridge
python src/main.py
```

## ⚙️ 설정

### **메인 설정 (config/app.yaml)**
- Input Layer 설정 (MQTT/SignalR)
- Transports Layer 설정
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
