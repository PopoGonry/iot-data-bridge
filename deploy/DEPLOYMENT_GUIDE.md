# 배포 가이드

각 VM에 필요한 파일만 복사하여 배포하는 방법을 설명합니다.

## 📦 배포 패키지

### **1. middleware-server/**
- **용도**: 중앙 서버 (MQTT 브로커 + SignalR Hub + IoT Data Bridge)
- **대상**: VM-1 (중앙 서버)
- **포함 파일**: 소스 코드, 설정 파일, SignalR Hub, MQTT 설정

### **2. data-source/**
- **용도**: 외부 데이터 전송
- **대상**: VM-2 (외부 데이터 소스)
- **포함 파일**: MQTT Publisher, 테스트 데이터

### **3. iot-device/**
- **용도**: IoT Device
- **대상**: VM-3~6 (각 Device VM)
- **포함 파일**: Device 실행 파일, 설정 파일

## 🚀 배포 단계

### **1. VM-1 (중앙 서버) 배포**
```bash
# 1. 파일 복사
scp -r deploy/middleware-server/ user@192.168.1.100:/opt/iot-data-bridge/

# 2. VM-1에서 실행
ssh user@192.168.1.100
cd /opt/iot-data-bridge

# 3. mosquitto_data 디렉토리 생성 (MQTT 브로커 데이터 저장용)
mkdir -p mosquitto_data

# 4. 의존성 설치 및 실행
pip install -r requirements.txt
./start.sh
```

### **2. VM-2 (외부 데이터) 배포**
```bash
# 1. 파일 복사
scp -r deploy/data-source/ user@192.168.1.101:/opt/data-source/

# 2. VM-2에서 실행
ssh user@192.168.1.101
cd /opt/data-source
pip install -r requirements.txt
./start.sh 192.168.1.100 1883
```

### **3. VM-3~6 (IoT Device) 배포**
```bash
# 1. 파일 복사
scp -r deploy/iot-device/ user@192.168.1.102:/opt/iot-device/

# 2. VM-3에서 실행
ssh user@192.168.1.102
cd /opt/iot-device
pip install -r requirements.txt
./start.sh VM-A

# 3. VM-4에서 실행
ssh user@192.168.1.103
cd /opt/iot-device
pip install -r requirements.txt
./start.sh VM-B

# 4. VM-5에서 실행
ssh user@192.168.1.104
cd /opt/iot-device
pip install -r requirements.txt
./start.sh VM-C

# 5. VM-6에서 실행
ssh user@192.168.1.105
cd /opt/iot-device
pip install -r requirements.txt
./start.sh VM-D
```

## ⚙️ 설정 수정

### **IP 주소 수정**
각 패키지의 설정 파일에서 실제 IP 주소로 수정:

1. **middleware-server/config/app-multi-vm.yaml**
2. **middleware-server/config/devices-multi-vm.yaml**
3. **iot-device/device_config.yaml**

### **Device ID 수정**
각 Device VM에서 고유한 Device ID 사용:
- VM-3: VM-A
- VM-4: VM-B
- VM-5: VM-C
- VM-6: VM-D

## 🔧 실행 순서

1. **VM-1**: 중앙 서버 시작
2. **VM-3~6**: IoT Device 시작
3. **VM-2**: 외부 데이터 전송

## 📊 모니터링

### **중앙 서버 로그**
```bash
# VM-1에서
tail -f /opt/iot-data-bridge/logs/iot_data_bridge.log
```

### **Device 로그**
```bash
# 각 Device VM에서
tail -f /opt/iot-device/device.log
```

### **MQTT 브로커 상태**
```bash
# VM-1에서
sudo systemctl status mosquitto
```

## 🐛 문제 해결

### **연결 실패**
- IP 주소 및 포트 확인
- 방화벽 설정 확인
- 네트워크 연결 상태 확인

### **서비스 시작 실패**
- 의존성 설치 확인
- 로그 파일 확인
- 권한 설정 확인

### **MQTT 브로커 데이터베이스 오류**
```
Error saving in-memory database, unable to open ./mosquitto_data//mosquitto.db.new for writing.
Error: No such file or directory.
```
**해결 방법:**
```bash
# mosquitto_data 디렉토리 생성
mkdir -p mosquitto_data

# 권한 설정 (필요한 경우)
chmod 755 mosquitto_data
```

### **데이터 전송 실패**
- MQTT 브로커 상태 확인
- 토픽 권한 확인
- 설정 파일 확인
