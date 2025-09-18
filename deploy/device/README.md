# IoT Device

IoT Data Bridge에서 전송된 데이터를 수신하고 처리하는 Device입니다.

## 🚀 설치 및 실행

### **1. 의존성 설치**
```bash
pip install -r requirements.txt
```

### **2. 설정 파일 수정**
`device_config.yaml`에서 브로커 IP 수정:
```yaml
device_id: "VM-A"  # Device ID 수정
mqtt:
  host: "192.168.1.100"  # 실제 브로커 IP
  port: 1883
  topic: "devices/vm-a/ingress"
```

### **3. 실행**
```bash
# Linux/Mac
./start.sh VM-A

# Windows
start.bat VM-A

# 직접 실행
python device.py VM-A device_config.yaml
```

## 📊 수신 데이터

Device는 다음 형식의 데이터를 수신합니다:
```json
{
  "object": "Geo.Latitude",
  "value": 37.5665,
  "timestamp": 1695123456.789
}
```

## ⚙️ 설정

### **Device ID별 설정**
```bash
# VM-A
python device.py VM-A

# VM-B
python device.py VM-B

# VM-C
python device.py VM-C

# VM-D
python device.py VM-D
```

### **설정 파일 커스터마이징**
```yaml
# device_config.yaml
device_id: "VM-A"
mqtt:
  host: "192.168.1.100"
  port: 1883
  topic: "devices/vm-a/ingress"
  qos: 1
  keepalive: 60
logging:
  level: "INFO"
  file: "device.log"
```

## 🔧 테스트

### **MQTT 구독 테스트**
```bash
# 수동으로 데이터 전송
mosquitto_pub -h 192.168.1.100 -p 1883 -t "devices/vm-a/ingress" -m '{"object":"Geo.Latitude","value":37.5665,"timestamp":1695123456.789}'
```

### **Device 로그 확인**
```bash
tail -f device.log
```

## 🐛 문제 해결

### **연결 실패**
- 브로커 IP 및 포트 확인
- 네트워크 연결 상태 확인
- 방화벽 설정 확인

### **데이터 수신 실패**
- MQTT 브로커 상태 확인
- 토픽 권한 확인
- Device 로그 확인

### **로그 파일 문제**
```bash
# 로그 디렉토리 권한 확인
ls -la device.log

# 로그 파일 크기 확인
du -h device.log
```