# IoT Data Bridge - 레이어별 DTO 흐름

## 📊 데이터 흐름 다이어그램

```
External Data → Input Layer → Mapping Layer → Resolver Layer → Transports Layer → Device
     ↓              ↓              ↓              ↓              ↓
   Raw Data    IngressEvent   MappedEvent   ResolvedEvent   TransportEvent
```

## 🔄 레이어별 DTO 상세

### 1. **Input Layer**
- **입력**: Raw Data (dict)
- **출력**: `IngressEvent`
- **책임**: 외부 데이터 수신 및 표준화

```python
class IngressEvent(BaseModel):
    trace_id: str
    raw: Dict[str, Any]      # 원본 데이터
    meta: Dict[str, Any]     # 메타데이터
    timestamp: datetime
```

### 2. **Mapping Layer**
- **입력**: `IngressEvent`
- **출력**: `MappedEvent`
- **책임**: 데이터를 Object로 매핑

```python
class MappedEvent(BaseModel):
    trace_id: str
    object: str              # 매핑된 Object 이름
    value: Any               # 매핑된 값
    value_type: ValueType    # 값 타입
    timestamp: datetime
```

### 3. **Resolver Layer**
- **입력**: `MappedEvent`
- **출력**: `ResolvedEvent`
- **책임**: 대상 Device 계산

```python
class ResolvedEvent(BaseModel):
    trace_id: str
    object: str
    value: Any
    target_devices: List[str]  # 대상 Device 목록
    timestamp: datetime
```

### 4. **Transports Layer**
- **입력**: `ResolvedEvent`
- **출력**: `TransportEvent`
- **책임**: Device별 전송 설정 및 실행

```python
class TransportEvent(BaseModel):
    trace_id: str
    device_targets: List[DeviceTarget]  # Device별 전송 설정
    timestamp: datetime

class DeviceTarget(BaseModel):
    device_id: str
    transport_config: TransportConfig
    object: str
    value: Any
```

### 5. **Logging Layer**
- **입력**: 각 레이어의 이벤트
- **출력**: 로그 파일
- **책임**: 이벤트 로깅

```python
class MiddlewareEventLog(BaseModel):
    timestamp: datetime
    trace_id: str
    raw: Dict[str, Any]
    object: str
    send_devices: List[str]

class DeviceIngestLog(BaseModel):
    timestamp: datetime
    device_id: str
    object: str
    value: Any
```

## 🔗 레이어 간 연결

### **Input → Mapping**
```python
# Input Layer에서
ingress_event = IngressEvent(
    trace_id=generate_trace_id(),
    raw=raw_data,
    meta=metadata
)
await mapping_layer.map_event(ingress_event)
```

### **Mapping → Resolver**
```python
# Mapping Layer에서
mapped_event = MappedEvent(
    trace_id=ingress_event.trace_id,
    object=mapping_rule.object,
    value=casted_value,
    value_type=mapping_rule.value_type
)
await resolver_layer.resolve_event(mapped_event)
```

### **Resolver → Transports**
```python
# Resolver Layer에서
resolved_event = ResolvedEvent(
    trace_id=mapped_event.trace_id,
    object=mapped_event.object,
    value=mapped_event.value,
    target_devices=device_list
)
await transports_layer.send_to_devices(resolved_event)
```

### **Transports → Logging**
```python
# Transports Layer에서
for device_target in device_targets:
    await logging_layer.log_device_ingest(DeviceIngestLog(
        device_id=device_target.device_id,
        object=device_target.object,
        value=device_target.value
    ))
```

## 🎯 레이어별 구현 순서

1. **Base Layer Interface** ✅
2. **Input Layer** (MQTT/SignalR 수신)
3. **Mapping Layer** (데이터 변환)
4. **Resolver Layer** (Device 계산)
5. **Transports Layer** (데이터 전송)
6. **Logging Layer** (이벤트 로깅)

## 🔍 각 레이어의 핵심 메서드

### **Input Layer**
- `start()`: MQTT/SignalR 연결 시작
- `process_raw_data()`: 원본 데이터 처리
- `stop()`: 연결 종료

### **Mapping Layer**
- `map_event()`: IngressEvent → MappedEvent 변환
- `_cast_value()`: 값 타입 캐스팅
- `_get_mapping_rule()`: 매핑 규칙 조회

### **Resolver Layer**
- `resolve_event()`: MappedEvent → ResolvedEvent 변환
- `_get_target_devices()`: 대상 Device 조회
- `_log_middleware_event()`: 미들웨어 이벤트 로깅

### **Transports Layer**
- `send_to_devices()`: Device별 데이터 전송
- `_resolve_transport_config()`: 전송 설정 해석
- `_send_mqtt()`: MQTT 전송
- `_send_signalr()`: SignalR 전송

### **Logging Layer**
- `log_middleware_event()`: 미들웨어 이벤트 로깅
- `log_device_ingest()`: Device 수신 로깅
- `_write_log()`: 로그 파일 쓰기

이제 각 레이어를 순차적으로 구현할 수 있습니다!
