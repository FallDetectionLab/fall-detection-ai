from flask import request, make_response, Response, redirect
import time
import cv2
import numpy as np
import json
import threading
from collections import deque

# stream_routes에서 update_latest_frame 함수 import
try:
    from routes.stream_routes import update_latest_frame
except ImportError:
    def update_latest_frame(frame):
        print("update_latest_frame not available")
        pass

try:
    from services.database_service import get_fall_events
except ImportError:
    def get_fall_events(limit=50):
        return []

# 실시간 알림을 위한 글로벌 변수
latest_notifications = deque(maxlen=50)
notification_lock = threading.Lock()

# 실시간 알림 대기열
notification_queue = deque(maxlen=100)
queue_lock = threading.Lock()

def broadcast_notification(notification):
    """모든 클라이언트에 알림 브로드캐스트"""
    with notification_lock:
        latest_notifications.appendleft(notification)
        
    with queue_lock:
        notification_queue.append(notification)
        
    print(f"📡 알림 브로드캐스트: {notification.get('message', 'No message')}")

def register_api_routes(app, detection_service, notification_manager):
    
    @app.route('/api/detect', methods=['POST'])
    def detect_frame():
        """라즈베리파이에서 프레임을 받아 낙상 감지 및 실제 프레임 저장"""
        try:
            if 'frame' not in request.files:
                return {'error': 'No frame provided'}, 400
            
            frame_file = request.files['frame']
            timestamp = request.form.get('timestamp')
            device_id = request.form.get('device_id', 'raspberry_pi')
            frame_number = request.form.get('frame_number', 0)
            
            # 프레임 디코딩
            frame_bytes = frame_file.read()
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {'error': 'Invalid frame data'}, 400
            
            # 전역 변수에 최신 프레임 저장 (비디오 녹화용)
            from services import frame_store
            frame_store.set_frame(frame)
            print(f"공유 프레임 저장소에 프레임 저장: {frame.shape}")
            
            # 실시간 스트리밍용 프레임 업데이트
            update_latest_frame(frame)

            # 낙상 감지 처리 (로그 최소화)
            result = detection_service.process_frame(frame, device_id, frame_number)
            
            # 낙상이 감지된 경우에만 로그 출력
            if result.get('fall_detected', False):
                print(f"🚨 낙상 감지됨! 신뢰도: {result.get('confidence', 0):.2f}")

            # 결과 후처리(녹화/알림/DB) - 낙상 감지시에만
            if result.get('fall_detected', False) and hasattr(detection_service, 'handle_detection_result'):
                try:
                    detection_service.handle_detection_result(result)
                except Exception as e:
                    print(f"[api_routes] handle_detection_result 실패: {e}")

            return {'success': True, 'detection': result}
                
        except Exception as e:
            print(f"라즈베리파이 Detect 오류: {e}")
            return {'error': str(e), 'success': False}, 500

    
    @app.route('/api/trigger-fall-detection', methods=['POST', 'OPTIONS'])
    def trigger_fall_detection():
        """수동 낙상 감지 트리거 (테스트용)"""
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "Content-Type")
            response.headers.add('Access-Control-Allow-Methods', "POST")
            return response
        
        try:
            data = request.get_json() or {}
            confidence = data.get('confidence', 0.9)
            
            print(f"🔥 수동 낙상 감지 트리거! 신뢰도: {confidence}")
            
            # DetectionService로 감지 결과 전달
            result = detection_service.trigger_manual_detection(confidence)
            
            # 낙상이 감지된 경우 실시간 알림 브로드캐스트
            if result.get('fall_detected', False):
                notification = {
                    'type': 'fall_alert',
                    'title': '🚨 낙상 감지 알림',
                    'message': f'낙상이 감지되었습니다! (신뢰도: {confidence:.1%})',
                    'confidence': confidence,
                    'timestamp': result.get('timestamp', time.time()),
                    'device_id': result.get('device_id', 'manual'),
                    'severity': 'high'
                }
                
                # 실시간 알림 브로드캐스트
                broadcast_notification(notification)
                print(f"📡 실시간 알림 브로드캐스트 완료: {notification['message']}")
            
            response_data = {
                'success': True,
                'message': '낙상 감지가 트리거되었습니다',
                'detection': result,
                'notification_broadcast': result.get('fall_detected', False)
            }
            
            response = make_response(response_data)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
            
        except Exception as e:
            print(f"❌ 수동 트리거 오류: {e}")
            error_response = {'error': str(e), 'success': False}
            response = make_response(error_response, 500)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
