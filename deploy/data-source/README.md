# Data Source

외부 데이터를 IoT Data Bridge로 전송하는 클라이언트입니다.

## 🚀 설치 및 실행

### **1. 자동 설치 (권장)**
```bash
# Linux/Mac
./install.sh

# Windows
install.bat
```

### **2. 수동 설치**
```bash
# 가상환경 생성 (권장)
python -m venv venv

# 가상환경 활성화
# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### **3. 실행**
```bash
# Linux/Mac (자동 의존성 확인 및 설치)
./start.sh 192.168.1.100 1883

# Windows (자동 의존성 확인 및 설치)
start.bat 192.168.1.100 1883

# 직접 실행
python test_mqtt_publisher-multi-vm.py 192.168.1.100 1883
```

### **4. 실행 예시**
```bash
# 로컬 MQTT 브로커에 연결
./start.sh localhost 1883

# 원격 MQTT 브로커에 연결
./start.sh 192.168.1.100 1883

# 다른 포트 사용
./start.sh 192.168.1.100 8883
```

## 📊 전송되는 데이터

- **GPS 데이터**: 위도, 경도, 고도
- **엔진 데이터**: RPM, 온도
- **환경 데이터**: 습도, 온도

## ⚙️ 설정

### **브로커 IP 수정**
`test_mqtt_publisher-multi-vm.py`에서 기본 IP 수정:
```python
broker_host = "192.168.1.100"  # 실제 브로커 IP
```

### **데이터 수정**
`test_mqtt_publisher-multi-vm.py`에서 테스트 데이터 수정:
```python
test_cases = [
    {
        "name": "Custom Data",
        "data": {
            "header": {
                "UUID": str(uuid.uuid4()),
                "TIME": datetime.now().strftime("%Y%m%d%H%M%S"),
                "SRC": "CUSTOM-GW-01",
                "DEST": "IoTDataBridge",
                "TYPE": "CUSTOMDATA"
            },
            "payload": {
                "Equip.Tag": "CUSTOM001",
                "Message.ID": "DATA001",
                "VALUE": 123.45
            }
        }
    }
]
```

## 🔧 테스트

### **연결 테스트**
```bash
# MQTT 브로커 연결 확인
python test_connection.py localhost 1883

# 성공 시: ✅ Connection successful!
# 실패 시: ❌ Connection failed: [오류 메시지]
```

### **데이터 전송 테스트**
```bash
# 테스트 데이터 전송
python test_mqtt_publisher-multi-vm.py localhost 1883

# 구독자로 수신 확인 (별도 터미널)
python test_mqtt_subscriber.py localhost 1883
```

### **외부 도구 테스트**
```bash
# mosquitto 클라이언트 사용
mosquitto_pub -h localhost -p 1883 -t "test/topic" -m "Hello World"
mosquitto_sub -h localhost -p 1883 -t "test/topic"
```

## 🐛 문제 해결

### **연결 실패**
- 브로커 IP 및 포트 확인
- 네트워크 연결 상태 확인
- 방화벽 설정 확인

### **데이터 전송 실패**
- MQTT 브로커 상태 확인
- 토픽 권한 확인
- 로그 확인