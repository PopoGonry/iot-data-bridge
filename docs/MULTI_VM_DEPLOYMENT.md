# 다중 VM 배포 가이드

IoT Data Bridge를 여러 VM에서 실행하는 방법을 설명합니다.

## 🏗️ VM 구성

### **VM-1: MQTT 브로커 + SignalR Hub + IoT Data Bridge**
- **역할**: 중앙 서버 (미들웨어)
- **IP**: `192.168.1.100` (예시)
- **서비스**: Mosquitto, SignalR Hub, IoT Data Bridge

### **VM-2: 외부 데이터 소스**
- **역할**: 외부 데이터 전송
- **IP**: `192.168.1.101` (예시)
- **서비스**: MQTT Publisher

### **VM-3~6: IoT Device**
- **역할**: 데이터 수신 및 처리
- **IP**: `192.168.1.102~105` (예시)
- **서비스**: IoT Device

## 🚀 배포 단계

### **1. VM-1 (중앙 서버) 설정**

```bash
# 1. 프로젝트 복사
git clone <repository> /opt/iot-data-bridge
cd /opt/iot-data-bridge

# 2. 의존성 설치
pip install -r requirements.txt

# 3. MQTT 브로커 설정 (mosquitto.conf 수정)
# bind_address 0.0.0.0  # 모든 인터페이스에서 수신
# port 1883

# 4. MQTT 브로커 시작
mosquitto -c middleware/mosquitto.conf

# 5. SignalR Hub 시작
cd middleware/signalr_hub
dotnet run

# 6. IoT Data Bridge 시작
cd middleware
python src/main.py --config config/app-multi-vm.yaml
```

### **2. VM-2 (외부 데이터 소스) 설정**

```bash
# 1. 필요한 파일만 복사
scp -r data_sources/ user@192.168.1.101:/opt/data-sources/

# 2. 의존성 설치
pip install aiomqtt

# 3. 데이터 전송
cd /opt/data-sources
python test_mqtt_publisher-multi-vm.py 192.168.1.100 1883
```

### **3. VM-3~6 (IoT Device) 설정**

```bash
# 1. Device 파일 복사
scp -r devices/ user@192.168.1.102:/opt/iot-device/

# 2. 의존성 설치
pip install aiomqtt structlog pyyaml

# 3. 설정 파일 수정
cd /opt/iot-device
cp device_config-multi-vm.yaml device_config.yaml
# device_config.yaml에서 IP 주소 수정

# 4. Device 실행
python device.py VM-A device_config.yaml
```

## ⚙️ 설정 파일 수정

### **MQTT 브로커 설정 (mosquitto.conf)**
```conf
# 모든 인터페이스에서 수신
bind_address 0.0.0.0
port 1883

# 로그 설정
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information

# 데이터 디렉토리
persistence true
persistence_location /var/lib/mosquitto/
```

### **방화벽 설정**
```bash
# MQTT 포트 (1883) 열기
sudo ufw allow 1883

# SignalR 포트 (5000) 열기
sudo ufw allow 5000
```

## 🔧 네트워크 연결 테스트

### **MQTT 연결 테스트**
```bash
# VM-2에서 VM-1의 MQTT 브로커 연결 테스트
mosquitto_pub -h 192.168.1.100 -p 1883 -t "test/topic" -m "Hello World"

# VM-3에서 구독 테스트
mosquitto_sub -h 192.168.1.100 -p 1883 -t "test/topic"
```

### **SignalR 연결 테스트**
```bash
# 웹 브라우저에서 접속
http://192.168.1.100:5000/hub
```

## 📊 실행 순서

1. **VM-1**: MQTT 브로커 + SignalR Hub + IoT Data Bridge 시작
2. **VM-3~6**: IoT Device 시작
3. **VM-2**: 외부 데이터 전송

## 🐛 문제 해결

### **연결 실패**
- 방화벽 설정 확인
- IP 주소 및 포트 확인
- 네트워크 연결 상태 확인

### **MQTT 연결 실패**
```bash
# MQTT 브로커 상태 확인
sudo systemctl status mosquitto

# 로그 확인
sudo tail -f /var/log/mosquitto/mosquitto.log
```

### **Device 연결 실패**
```bash
# Device 로그 확인
tail -f device.log

# MQTT 브로커 연결 테스트
mosquitto_pub -h 192.168.1.100 -p 1883 -t "devices/vm-a/ingress" -m '{"object":"Geo.Latitude","value":37.5665,"timestamp":1695123456.789}'
```

## 📝 주의사항

1. **IP 주소**: 실제 환경에 맞게 IP 주소 수정
2. **보안**: 프로덕션 환경에서는 인증 및 암호화 설정
3. **모니터링**: 각 VM의 리소스 사용량 모니터링
4. **백업**: 설정 파일 및 로그 백업
