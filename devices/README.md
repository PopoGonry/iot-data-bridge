# Devices - IoT Device

IoT Data Bridge에서 전송된 데이터를 수신하고 처리하는 Device입니다.

## 📁 파일 구조

```
devices/
├── device.py                      # Device 실행 파일 (명령행 인수 사용)
├── start.bat                      # Windows 실행 스크립트
├── start.sh                       # Linux/macOS 실행 스크립트
├── requirements.txt               # 프로젝트 의존성
└── README.md                     # 이 파일
```

## 🚀 실행 방법

### **간편 실행 (추천)**
```bash
# Windows
start.bat

# Linux/macOS
./start.sh
```

### **명령행 인수 사용**
```bash
# Device ID, MQTT 호스트, 포트 지정
python device.py VM-A localhost 1883
python device.py VM-B 192.168.1.100 1883
python device.py MyDevice mqtt.example.com 1883

# Device ID만 지정 (기본값: localhost:1883)
python device.py VM-A
```

## ⚙️ 설정

### **명령행 인수**
- `device_id`: Device ID (필수)
- `mqtt_host`: MQTT 브로커 호스트 (기본값: localhost)
- `mqtt_port`: MQTT 브로커 포트 (기본값: 1883)

### **자동 생성되는 설정**
```yaml
device_id: "VM-A"  # 명령행에서 지정
mqtt:
  host: "localhost"  # 명령행에서 지정
  port: 1883         # 명령행에서 지정
  topic: "devices/vm-a/ingress"  # device_id 기반 자동 생성
  qos: 1
  keepalive: 60
logging:
  level: "INFO"
  file: "device.log"
  max_size: 10485760
  backup_count: 5
```

## 📊 수신 데이터 형식

```json
{
  "object": "Geo.Latitude",
  "value": 37.5665,
  "timestamp": 1695123456.789
}
```

## 🎯 Device 동작

1. **MQTT 토픽 구독**: `devices/{device_id}/ingress`
2. **데이터 수신**: Object와 Value 받기
3. **로그 기록**: 수신한 데이터를 통일된 포맷으로 출력
4. **히스토리 관리**: 최근 데이터 포인트 보관

## 📝 로그

### **콘솔 로그**
```
Starting IoT Device: VM-A
MQTT Host: localhost:1883
Device VM-A configuration:
  - MQTT Host: localhost:1883
  - Topic: devices/vm-a/ingress

17:57:41 | INFO | Data received | device_id=VM-A | object=Geo.Latitude | value=37.4558
17:57:41 | INFO | Data received | device_id=VM-A | object=Geo.Longitude | value=126.2904
```

### **파일 로그**
- **위치**: `logs/device.log`
- **포맷**: 콘솔 로그와 동일한 `Data received` 형태
- **내용**: 수신한 모든 데이터 기록

## 🚀 VM별 배포

### **각 VM에서 실행**
```bash
# VM-A에서
python device.py VM-A localhost 1883

# VM-B에서 (다른 MQTT 브로커)
python device.py VM-B 192.168.1.100 1883
```

### **start.sh 스크립트 사용**
```bash
# 대화형으로 설정 입력
./start.sh
# Enter Device ID (default: VM-A): VM-A
# Enter MQTT broker host (default: localhost): 192.168.1.100
# Enter MQTT broker port (default: 1883): 1883
```
