# Data Sources - 외부 데이터 소스

외부에서 IoT Data Bridge로 데이터를 전송하는 부분입니다.

## 📁 파일 구조

```
data-sources/
├── mqtt_publisher.py              # MQTT 데이터 발행기
├── data_generator.py              # 외부 데이터 생성기
├── start.bat                      # Windows 실행 스크립트
├── start.sh                       # Linux/macOS 실행 스크립트
└── requirements.txt               # 프로젝트 의존성
```

## 🚀 사용 방법

### **간편 실행 (추천)**
```bash
# Windows
start.bat

# Linux/macOS
./start.sh
```

### **직접 실행**
```bash
# MQTT로 데이터 전송 (5초마다 랜덤 데이터)
# 사용법: python mqtt_publisher.py <broker_host> <broker_port>

# 로컬 환경
python mqtt_publisher.py localhost 1883

# 원격 환경 (middleware 서버)
python mqtt_publisher.py 192.168.32.102 1883

# 명령행 인수 필수 (없으면 사용법 안내 표시)
python mqtt_publisher.py
# Usage Examples:
#    Local:    python3 mqtt_publisher.py localhost 1883
#    Remote:   python3 mqtt_publisher.py 192.168.1.100 1883
```

### **데이터 생성**
```bash
# 데이터 예시 출력
python data_generator.py
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

## 📝 로그

### **콘솔 로그**
```
Starting IoT Data Publisher
Connecting to MQTT broker at 192.168.32.102:1883
Publishing to topic: iot/ingress
Interval: 5 seconds
Press Ctrl+C to stop

Starting with broker: 192.168.32.102:1883
Cycle 1: Publishing random data...
Cycle 2: Publishing random data...
```

### **특징**
- ✅ **주기적 전송**: 5초마다 랜덤 데이터 전송
- ✅ **모든 객체 포함**: GPS, Engine, Environment 데이터 모두 생성
- ✅ **Graceful Shutdown**: Ctrl+C로 안전한 종료
- ✅ **명령행 인수 필수**: broker_host, broker_port 반드시 지정
