"""알림 서비스 - 하위 호환성"""
import time

def add_fall_alert(event_id, confidence, bbox):
    """낙상 알림 추가 (하위 호환성)"""
    print(f"[ALERT] Fall alert added: event_id={event_id}, confidence={confidence}")
    
    try:
        from services.notification_service import notification_manager
        notification_manager.add_fall_notification(
            confidence=confidence,
            event_id=event_id
        )
    except ImportError:
        print("[ALERT] Notification manager not available")

def create_notification(title, message, notification_type="info"):
    """알림 생성 (하위 호환성)"""
    try:
        from services.notification_service import create_notification as real_create
        return real_create(title, message, notification_type)
    except ImportError:
        return {'id': int(time.time()), 'title': title, 'message': message}

def add_fall_alert(event_id, confidence, bbox):
    """낙상 알람 추가"""
    global fall_event_queue
    
    alert_data = {
        'event_id': event_id,
        'timestamp': time.time(),
        'confidence': confidence,
        'bbox': bbox
    }
    
    fall_event_queue.append(alert_data)
    print(f"🚨 낙상 알람 추가됨 - 이벤트 ID: {event_id}")
    
    # notification_service와 연동
    create_notification(
        title="낙상 감지 알람",
        message=f"낙상이 감지되었습니다. 신뢰도: {confidence:.2f}",
        notification_type="fall_detected",
        severity="high"
    )

def get_pending_alerts():
    """처리되지 않은 알람 가져오기"""
    global fall_event_queue
    
    if fall_event_queue:
        alerts = fall_event_queue.copy()
        fall_event_queue.clear()
        return alerts
    return []

def clear_alerts():
    """모든 알람 지우기"""
    global fall_event_queue
    fall_event_queue.clear()
