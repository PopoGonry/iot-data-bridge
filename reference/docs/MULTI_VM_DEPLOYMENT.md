# 다중 VM 배포 가이드

IoT Data Bridge를 여러 VM에서 실행하는 방법을 설명합니다.

## 🏗️ VM 구성

### **VM-1: IoT Data Bridge Middleware**
- **역할**: 중앙 서버 (미들웨어)
- **IP**: `192.168.32.102` (예시)
- **서비스**: 자동 MQTT 브로커, IoT Data Bridge

### **VM-2: 외부 데이터 소스**
- **역할**: 외부 데이터 전송
- **IP**: `192.168.32.103` (예시)
- **서비스**: MQTT Publisher

### **VM-3~4: IoT Device**
- **역할**: 데이터 수신 및 처리
- **IP**: `192.168.32.104~105` (예시)
- **서비스**: IoT Device (VM-A, VM-B)

## 🚀 배포 단계

### **1. VM-1 (중앙 서버) 설정**

```bash
# 1. 프로젝트 복사
git clone <repository> /opt/iot-data-bridge
cd /opt/iot-data-bridge

# 2. 의존성 설치
cd middleware
pip install -r requirements-mqtt.txt

# 3. IoT Data Bridge 시작 (MQTT 브로커 자동 시작)
./start-mqtt.sh

# 또는 직접 실행
python src/main_mqtt.py
```

### **2. VM-2 (외부 데이터 소스) 설정**

```bash
# 1. 필요한 파일만 복사
scp -r data-sources/ user@192.168.32.103:/opt/data-sources/

# 2. 의존성 설치
cd /opt/data-sources
pip install -r requirements.txt

# 3. 데이터 전송 (MQTT 버전)
python mqtt_publisher.py 192.168.32.102 1883

# 또는 start-mqtt.sh 스크립트 사용
./start-mqtt.sh

# 3. 데이터 전송 (SignalR 버전)
python signalr_publisher.py http://192.168.32.102:5000/hub iot_clients

# 또는 start-signalr.sh 스크립트 사용
./start-signalr.sh
```

### **3. VM-3~4 (IoT Device) 설정**

```bash
# 1. Device 파일 복사
scp -r devices/ user@192.168.32.104:/opt/iot-device/

# 2. 의존성 설치
cd /opt/iot-device
pip install -r requirements.txt

# 3. Device 실행 (MQTT 버전)
python device.py VM-A 192.168.32.102 1883

# 또는 start-mqtt.sh 스크립트 사용
./start-mqtt.sh
# Enter Device ID (default: VM-A): VM-A
# Enter MQTT broker host (default: localhost): 192.168.32.102
# Enter MQTT broker port (default: 1883): 1883

# 3. Device 실행 (SignalR 버전)
python signalr_device.py VM-A http://192.168.32.102:5000/hub VM-A

# 또는 start-signalr.sh 스크립트 사용
./start-signalr.sh
# Enter Device ID (default: VM-A): VM-A
# Enter SignalR hub URL (default: http://localhost:5000/hub): http://192.168.32.102:5000/hub
# Enter Group name (default: VM-A): VM-A
```

## ⚙️ 설정 파일 수정

### **MQTT 브로커 설정 (mosquitto.conf)**
```conf
# 모든 인터페이스에서 수신
listener 1883 0.0.0.0
allow_anonymous true

# 로그 설정
log_dest stdout
log_type error
log_type warning
log_type notice
log_type information
log_type debug

# 데이터 디렉토리
persistence true
persistence_location ./mosquitto_data/
```

### **방화벽 설정**
```bash
# MQTT 포트 (1883) 열기
sudo ufw allow 1883
```

## 🔧 네트워크 연결 테스트

### **MQTT 연결 테스트**
```bash
# VM-2에서 VM-1의 MQTT 브로커 연결 테스트
mosquitto_pub -h 192.168.32.102 -p 1883 -t "test/topic" -m "Hello World"

# VM-3에서 구독 테스트
mosquitto_sub -h 192.168.32.102 -p 1883 -t "test/topic"
```

## 📊 실행 순서

1. **VM-1**: IoT Data Bridge Middleware 시작 (MQTT 브로커 자동 시작)
2. **VM-3~4**: IoT Device 시작
3. **VM-2**: 외부 데이터 전송

## 📝 로그 확인

### **Middleware 로그**
```bash
# VM-1에서
tail -f middleware/logs/iot_data_bridge.log
# 2025-09-19 17:57:41 | INFO | Data sent | device_id=VM-A | object=Geo.Latitude | value=37.4558
```

### **Device 로그**
```bash
# VM-3에서
tail -f devices/logs/device.log
# 2025-09-19 17:57:41 | INFO | Data received | device_id=VM-A | object=Geo.Latitude | value=37.4558
```

## 🐛 문제 해결

### **연결 실패**
- 방화벽 설정 확인
- IP 주소 및 포트 확인
- 네트워크 연결 상태 확인

### **MQTT 연결 실패**
```bash
# MQTT 브로커 상태 확인 (middleware가 자동으로 시작)
ps aux | grep mosquitto

# 포트 확인
netstat -tlnp | grep 1883
```

### **Device 연결 실패**
```bash
# Device 로그 확인
tail -f devices/logs/device.log

# MQTT 브로커 연결 테스트
mosquitto_pub -h 192.168.32.102 -p 1883 -t "devices/vm-a/ingress" -m '{"object":"Geo.Latitude","value":37.5665,"timestamp":1695123456.789}'
```

## 📝 주의사항

1. **IP 주소**: 실제 환경에 맞게 IP 주소 수정
2. **보안**: 프로덕션 환경에서는 인증 및 암호화 설정
3. **모니터링**: 각 VM의 리소스 사용량 모니터링
4. **백업**: 설정 파일 및 로그 백업
