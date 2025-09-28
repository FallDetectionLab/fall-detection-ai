from flask import Response
import cv2
import numpy as np
import time
import threading
from collections import deque

# 전역 프레임 버퍼 (라즈베리파이에서 받은 실제 프레임들)
latest_frame_buffer = deque(maxlen=30)  # 최근 30프레임 유지
latest_frame_lock = threading.Lock()
latest_frame = None
last_frame_time = 0

def update_latest_frame(frame):
    """라즈베리파이에서 받은 프레임 업데이트"""
    global latest_frame, last_frame_time
    
    with latest_frame_lock:
        latest_frame = frame.copy()
        last_frame_time = time.time()
        latest_frame_buffer.append(frame.copy())
    
    # 디버그 로그 (너무 많이 출력되지 않도록 제한)
    if int(time.time()) % 5 == 0:  # 5초마다 한 번
        print(f"📹 실시간 프레임 업데이트됨 (버퍼 크기: {len(latest_frame_buffer)})")

def get_current_frame():
    """현재 프레임 가져오기 (실제 프레임 우선, 없으면 더미)"""
    global latest_frame, last_frame_time
    
    with latest_frame_lock:
        # 5초 이내의 신선한 프레임이 있으면 사용
        if latest_frame is not None and (time.time() - last_frame_time) < 5.0:
            return latest_frame.copy()
    
    # 오래된 프레임이거나 없으면 더미 프레임 생성
    return create_dummy_frame()

def create_dummy_frame():
    """더미 프레임 생성 (연결 대기 상태)"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 동적 배경
    t = time.time()
    for y in range(480):
        color_val = int(30 + 20 * np.sin(t + y * 0.01))
        frame[y, :] = [color_val, color_val, color_val]
    
    cv2.putText(frame, "SafeFall Live Stream", (150, 200), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, "Waiting for Pi Camera...", (140, 250), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
    
    # 시간 표시
    current_time = time.strftime("%H:%M:%S")
    cv2.putText(frame, current_time, (250, 300), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    return frame

def register_stream_routes(app, streaming_handler):
    
    @app.route('/api/video_feed')
    def video_feed():
        """메인 비디오 피드 (실제 라즈베리파이 프레임 사용)"""
        def generate():
            print("📺 실시간 스트림 시작 (real Pi frames)")
            while True:
                try:
                    # 실제 라즈베리파이 프레임 사용
                    frame = get_current_frame()
                    
                    # JPEG 인코딩
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    time.sleep(0.033)  # ~30fps
                    
                except Exception as e:
                    print(f"❌ Stream error: {e}")
                    time.sleep(0.1)
                    
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @app.route('/api/stream/live')
    def live_stream():
        """라이브 스트림 (별칭)"""
        return video_feed()
    
    @app.route('/api/frame/latest')
    def get_latest_frame():
        """최신 프레임 이미지 (실제 라즈베리파이 프레임)"""
        try:
            frame = get_current_frame()
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                return Response(buffer.tobytes(), mimetype='image/jpeg')
            
            return Response(b'', mimetype='image/jpeg', status=500)
            
        except Exception as e:
            print(f"❌ Latest frame 오류: {e}")
            return Response(b'', mimetype='image/jpeg', status=500)
    
    @app.route('/api/stream/ping', methods=['GET'])
    def stream_ping():
        """스트림 핑 (라즈베리파이용)"""
        return {
            'status': 'ok',
            'timestamp': time.time(),
            'fallback_age_ms': 0,
            'server': 'SafeFall Backend'
        }
