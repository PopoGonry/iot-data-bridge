# Devices - IoT Device

IoT Data Bridge에서 전송된 데이터를 수신하고 처리하는 Device입니다.

## 📁 파일 구조

```
devices/
├── device.py               # Device 실행 파일
├── device_config.yaml      # Device 설정 템플릿
└── README.md              # 이 파일
```

## 🚀 실행 방법

### **기본 실행**
```bash
# Device ID만 지정 (기본 설정 사용)
python device.py VM-A
python device.py VM-B
python device.py VM-C
python device.py VM-D
```

### **MQTT 호스트/포트 지정**
```bash
# MQTT 브로커 정보 지정
python device.py VM-A localhost 1883
python device.py MyDevice mqtt.example.com 1883
```

### **설정 파일 사용**
```bash
# 설정 파일과 함께 실행
python device.py VM-A device_config.yaml
```

## ⚙️ 설정

### **설정 파일 (device_config.yaml)**
```yaml
device_id: "VM-A"
mqtt:
  host: "localhost"
  port: 1883
  topic: "devices/vm-a/ingress"
  qos: 1
  keepalive: 60
logging:
  level: "INFO"
  file: "device.log"
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
3. **로그 기록**: 수신한 데이터를 JSON 로그로 출력
4. **히스토리 관리**: 최근 데이터 포인트 보관

## 🚀 VM별 배포

### **각 VM에서 실행**
```bash
# VM-A에서
python device.py VM-A

# VM-B에서  
python device.py VM-B

# VM-C에서
python device.py VM-C

# VM-D에서
python device.py VM-D
```

### **설정 파일 커스터마이징**
```bash
# VM-A용 설정 파일 생성
cp device_config.yaml vm-a-config.yaml
# vm-a-config.yaml 수정 후
python device.py VM-A vm-a-config.yaml
```
