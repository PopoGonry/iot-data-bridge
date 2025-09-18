# IoT Data Bridge Middleware Server

중앙 서버에서 실행되는 IoT Data Bridge 미들웨어입니다.

## 🚀 설치 및 실행

### **1. 의존성 설치**
```bash
pip install -r requirements.txt
```

### **2. MQTT 브로커 설치 (Ubuntu/Debian)**
```bash
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients
```

### **3. .NET 설치 (SignalR Hub용)**
```bash
# Ubuntu/Debian
wget https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt-get update
sudo apt-get install -y dotnet-sdk-6.0
```

### **4. 실행**
```bash
# Linux/Mac (선택 메뉴)
./start.sh

# Linux/Mac (MQTT만)
./start-mqtt-only.sh

# Linux/Mac (SignalR만)
./start-signalr-only.sh

# Windows (MQTT만)
start-mqtt-only.bat

# Windows (SignalR만)
start-signalr-only.bat
```

### **5. 실행 권한 설정 (Linux/Mac)**
```bash
chmod +x start.sh
chmod +x start-mqtt-only.sh
chmod +x start-signalr-only.sh
```

## ⚙️ 설정

### **IP 주소 수정**
`config/app-multi-vm.yaml`에서 실제 서버 IP로 수정:
```yaml
input:
  mqtt:
    host: "192.168.1.100"  # 실제 서버 IP
transports:
  mqtt:
    host: "192.168.1.100"  # 실제 서버 IP
```

### **방화벽 설정**
```bash
# MQTT 포트 (1883) 열기
sudo ufw allow 1883

# SignalR 포트 (5000) 열기
sudo ufw allow 5000
```

## 📊 서비스 확인

### **MQTT 브로커 상태**
```bash
sudo systemctl status mosquitto
```

### **SignalR Hub 확인**
웹 브라우저에서 `http://서버IP:5000/hub` 접속

### **IoT Data Bridge 로그**
```bash
tail -f logs/iot_data_bridge.log
```

## 🛠️ 문제 해결

### **MQTT 브로커 시작 실패**
```bash
# 로그 확인
sudo tail -f /var/log/mosquitto/mosquitto.log

# 설정 파일 확인
mosquitto -c mosquitto.conf -v
```

### **SignalR Hub 시작 실패**
```bash
cd signalr_hub
dotnet run
```

### **포트 충돌**
```bash
# 포트 사용 확인
netstat -tlnp | grep :1883
netstat -tlnp | grep :5000
```
