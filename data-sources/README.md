# Data Sources - 외부 데이터 소스

외부에서 IoT Data Bridge로 해양 장비 데이터를 전송하는 부분입니다.
NMEA 및 해양 장비 사양에 기반한 완전한 해양 장비 데이터를 생성하고 전송합니다.

## 📁 파일 구조

```
data-sources/
├── mqtt_publisher.py              # MQTT 데이터 발행기
├── signalr_publisher.py           # SignalR 데이터 발행기
├── data_generator.py              # 외부 데이터 생성기
├── start-mqtt.bat                 # MQTT Windows 실행 스크립트
├── start-mqtt.sh                  # MQTT Linux/macOS 실행 스크립트
├── start-signalr.bat              # SignalR Windows 실행 스크립트
├── start-signalr.sh               # SignalR Linux/macOS 실행 스크립트
└── requirements.txt               # 프로젝트 의존성
```

## 🚀 사용 방법

### **간편 실행 (추천)**

#### **MQTT 버전**
```bash
# Windows
start-mqtt.bat

# Linux/macOS
./start-mqtt.sh
```

#### **SignalR 버전**
```bash
# Windows
start-signalr.bat

# Linux/macOS
./start-signalr.sh
```

### **직접 실행**

#### **MQTT 버전**
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

#### **SignalR 버전**
```bash
# SignalR로 데이터 전송 (5초마다 랜덤 데이터)
# 사용법: python signalr_publisher.py <hub_url> [group_name]

# 로컬 환경
python signalr_publisher.py http://localhost:5000/hub iot_clients

# 원격 환경 (middleware 서버)
python signalr_publisher.py http://192.168.32.102:5000/hub iot_clients

# 명령행 인수 필수 (없으면 사용법 안내 표시)
python signalr_publisher.py
# Usage Examples:
#    Local:    python3 signalr_publisher.py http://localhost:5000/hub iot_clients
#    Remote:   python3 signalr_publisher.py http://192.168.1.100:5000/hub iot_clients
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
    "SRC": "GPS-GW-01",
    "DEST": "IoTDataBridge",
    "TYPE": "GPSDATA"
  },
  "payload": {
    "Equip.Tag": "GPS001",
    "Message.ID": "GLL001",
    "VALUE": 37.5665
  }
}
```

## 🎯 해양 장비 데이터 시나리오

### **GPS Navigation Data**
- GPS 위도/경도 (GLL001, GLL002)
- GPS 코스 오버 그라운드 (VTG001)
- GPS 스피드 오버 그라운드 (VTG002)

### **Speed Log Data**
- 물을 통한 속도 (VHW003)

### **Wind Data**
- 풍향/풍속/참조점/단위 (MWV101-104)

### **Echo Sounder Data**
- 수심/수온 (DPT101, MTW001)

### **Engine Data**
- Engine 1/2: 데이터 소스, 샤프트 번호, 속도, 프로펠러 피치, 상태
- Diesel Engine 1: 9개 실린더 배기 가스 온도/최대 압력, 시스템 데이터
- Gas Engine 1: 배기 가스 온도, 윤활유 압력, RPM

### **Rudder Data**
- 좌우 러더 각도/상태 (RSA001-004)

### **VDR Data**
- 해류 설정/드리프트 (VDR001-002)

### **Inclinometer Data**
- 롤/피치 각도 (XDR001-002)

### **Gyrocompass Data**
- 자기 방향/진북 방향 (HDG001, THS001)

### **Diesel Generator Data**
- Generator 1/2 운전 시간

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
- ✅ **주기적 전송**: 5초마다 랜덤 해양 장비 데이터 전송
- ✅ **완전한 해양 장비 데이터**: GPS, Wind, Engine, Rudder, VDR, Inclinometer, Gyrocompass, Diesel Engine, Gas Engine, Generator 등 66개 데이터 포인트
- ✅ **NMEA 표준 준수**: 해양 장비 표준에 따른 데이터 형식
- ✅ **VM 매핑 지원**: devices.yaml과 mappings.yaml에 정의된 매핑 규칙 완전 지원
- ✅ **Graceful Shutdown**: Ctrl+C로 안전한 종료
- ✅ **명령행 인수 필수**: broker_host, broker_port 반드시 지정
