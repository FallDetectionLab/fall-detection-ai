"""알림 및 경고 서비스"""
import time
import threading
from datetime import datetime, timedelta
from collections import deque

class NotificationManager:
    def __init__(self, max_notifications=100):
        self.notifications = deque(maxlen=max_notifications)
        self.lock = threading.Lock()
        
    def add_fall_notification(self, confidence, timestamp=None, device_id="unknown", event_id=None):
        """낙상 감지 알림 추가"""
        if timestamp is None:
            timestamp = time.time()
            
        notification = {
            'id': f"fall_{int(timestamp * 1000)}",
            'type': 'fall_detection',
            'title': '낙상 감지',
            'message': f'낙상이 감지되었습니다 (신뢰도: {confidence:.1%})',
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'confidence': confidence,
            'device_id': device_id,
            'event_id': event_id,
            'read': False,
            'severity': 'high' if confidence > 0.8 else 'medium'
        }
        
        with self.lock:
            self.notifications.appendleft(notification)
            
        print(f"📢 알림 추가: {notification['message']}")
        return notification
    
    def get_latest_notifications(self, limit=10):
        """최신 알림 목록 반환"""
        with self.lock:
            return list(self.notifications)[:limit]
    
    def get_unread_count(self):
        """읽지 않은 알림 수"""
        with self.lock:
            return sum(1 for n in self.notifications if not n['read'])
    
    def mark_as_read(self, notification_id):
        """알림을 읽음으로 표시"""
        with self.lock:
            for notification in self.notifications:
                if notification['id'] == notification_id:
                    notification['read'] = True
                    return True
        return False
    
    def get_stats(self):
        """알림 통계"""
        with self.lock:
            total = len(self.notifications)
            unread = sum(1 for n in self.notifications if not n['read'])
            fall_count_today = sum(1 for n in self.notifications 
                                 if n['type'] == 'fall_detection' and 
                                 datetime.fromtimestamp(n['timestamp']).date() == datetime.now().date())
            
            return {
                'total_notifications': total,
                'unread_count': unread,
                'fall_detections_today': fall_count_today,
                'last_notification': self.notifications[0]['timestamp'] if self.notifications else None
            }

# 전역 인스턴스 (기존 호환성)
notification_manager = NotificationManager()

def get_latest_notifications(limit=10):
    return notification_manager.get_latest_notifications(limit)

def get_pending_alerts():
    return [n for n in notification_manager.get_latest_notifications() if not n['read']]

def get_notification_stats():
    return notification_manager.get_stats()

def create_notification(title, message, notification_type="info", event_id=None):
    """알림 생성 함수 (하위 호환성)"""
    notification = {
        'id': f"notif_{int(time.time() * 1000)}",
        'type': notification_type,
        'title': title,
        'message': message,
        'timestamp': time.time(),
        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'event_id': event_id,
        'read': False,
        'severity': 'high' if notification_type == 'fall_detection' else 'medium'
    }
    
    with notification_manager.lock:
        notification_manager.notifications.appendleft(notification)
    
    return notification

def add_fall_detection(detection_data):
    """낙상 감지 알림 추가 (하위 호환성)"""
    return notification_manager.add_fall_notification(
        confidence=detection_data.get('confidence', 0.8),
        timestamp=detection_data.get('timestamp'),
        device_id=detection_data.get('device_id', 'unknown'),
        event_id=detection_data.get('event_id')
    )
