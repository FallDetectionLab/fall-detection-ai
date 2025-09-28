"""라즈베리파이 카메라 스트리밍 서비스 (프론트엔드 호환)"""
import cv2
import numpy as np
import time
import threading
import sys
import os
from flask import Response
from threading import Lock
import base64

# 다른 서비스들 import (선택적)
current_dir = os.path.dirname(__file__)
utils_dir = os.path.join(os.path.dirname(current_dir), 'utils')
sys.path.insert(0, current_dir)
sys.path.insert(0, utils_dir)

try:
    from video_service import get_camera_manager_with_buffer
    CAMERA_MANAGER_AVAILABLE = True
except ImportError:
    CAMERA_MANAGER_AVAILABLE = False

try:
    from detection_service import detect_fall_in_frame_with_recording
    DETECTION_SERVICE_AVAILABLE = True
except ImportError:
    DETECTION_SERVICE_AVAILABLE = False

try:
    from utils.app_utils import get_latest_detection_result, set_simulation_mode
    APP_UTILS_AVAILABLE = True
except ImportError:
    APP_UTILS_AVAILABLE = False
    def get_latest_detection_result():
        return {'fall_detected': False, 'confidence': 0.0}
    def set_simulation_mode(enable):
        return enable

class StreamingHandler:
    """라즈베리파이 카메라 스트리밍 처리 클래스 (프론트엔드 호환)"""
    
    def __init__(self):
        self.camera_manager = None
        self.camera = None
        self.active = False
        self.frame_count = 0
        self.detection_active = False
        self.latest_frame = None
        self.video_service = None
        self.lock = Lock()
        self._dummy_frame_thread = None
        self._should_generate_dummy = True
        
        # 시작 시 더미 프레임 생성 시작
        self._start_dummy_frame_generation()
    
    def _start_dummy_frame_generation(self):
        """더미 프레임 생성 스레드 시작"""
        if self._dummy_frame_thread is None or not self._dummy_frame_thread.is_alive():
            self._dummy_frame_thread = threading.Thread(target=self._generate_dummy_frames, daemon=True)
            self._dummy_frame_thread.start()
            print("✅ 더미 프레임 생성 시작 (대시보드용)")
    
    def _generate_dummy_frames(self):
        """지속적으로 더미 프레임 생성"""
        import threading
        frame_counter = 0
        
        while self._should_generate_dummy:
            try:
                # 실제 카메라가 연결되지 않은 경우에만 더미 프레임 생성
                if self.camera is None or not self.active:
                    dummy_frame = self._create_demo_frame(frame_counter)
                    with self.lock:
                        self.latest_frame = dummy_frame
                        # VideoService에는 add_frame 메서드가 없으므로 제거
                    frame_counter += 1
                
                time.sleep(0.1)  # 10 FPS
                
            except Exception as e:
                print(f"❌ 더미 프레임 생성 오류: {e}")
                time.sleep(1)
    
    def _create_demo_frame(self, frame_number):
        """데모용 프레임 생성"""
        import numpy as np
        from datetime import datetime
        
        # 640x480 프레임 생성
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 동적 배경 (시간에 따라 변화)
        t = time.time()
        for y in range(480):
            for x in range(640):
                r = int(50 + 30 * np.sin(t + x * 0.01))
                g = int(50 + 30 * np.sin(t + y * 0.01 + 1))
                b = int(50 + 30 * np.sin(t + (x + y) * 0.005 + 2))
                frame[y, x] = [max(0, min(255, b)), max(0, min(255, g)), max(0, min(255, r))]
        
        # SafeFall 로고/텍스트
        cv2.putText(frame, "SafeFall Live Demo", (180, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        cv2.putText(frame, "SafeFall Live Demo", (180, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)
        
        # 현재 시간
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, current_time, (200, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 프레임 카운터
        cv2.putText(frame, f"Frame: {frame_number:06d}", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 상태 표시
        cv2.putText(frame, "Status: Demo Mode", (50, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.putText(frame, "Waiting for Pi Camera...", (50, 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 2)
        
        # 낙상 감지 상태
        if hasattr(self, '_last_detection_time') and time.time() - self._last_detection_time < 5:
            cv2.putText(frame, "FALL DETECTED!", (200, 300), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        else:
            cv2.putText(frame, "Monitoring...", (250, 300), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        
        # 프레임 경계선
        cv2.rectangle(frame, (10, 10), (630, 470), (100, 100, 100), 2)
        
        return frame
    
    def set_video_service(self, video_service):
        """비디오 서비스 설정"""
        self.video_service = video_service
        print("✅ 스트리밍 핸들러에 비디오 서비스 연결됨")
    
    def get_video_stream(self):
        """비디오 스트림 생성 (호환성 메소드)"""
        return self.generate_frames()
    
    def start(self):
        """카메라 시작"""
        try:
            print("🎥 카메라 시작...")
            
            if CAMERA_MANAGER_AVAILABLE:
                # 버퍼링 기능이 있는 카메라 매니저 사용
                self.camera_manager = get_camera_manager_with_buffer()
                self.camera = self.camera_manager.initialize_camera()
                
                if self.camera is None:
                    return {
                        'error': '라즈베리파이 카메라 초기화 실패',
                        'success': False,
                        'suggestions': [
                            'sudo raspi-config에서 카메라 활성화',
                            'rpicam-vid --list-cameras로 카메라 확인'
                        ]
                    }
                
                # 영상 버퍼링 시작 (전후 30초 저장용)
                if hasattr(self.camera_manager, 'start_buffering'):
                    self.camera_manager.detection_active = True
                    self.camera_manager.start_buffering()
                    print("📹 영상 버퍼링 시작 (전후 30초)")
            else:
                # 일반 웹캠 사용
                self.camera = cv2.VideoCapture(0)
                if not self.camera.isOpened():
                    return {
                        'error': '카메라 초기화 실패',
                        'success': False
                    }
            
            self.active = True
            self.detection_active = True
            
            return {
                'message': '카메라 시작됨',
                'status': 'active',
                'buffering': 'enabled' if CAMERA_MANAGER_AVAILABLE else 'disabled',
                'success': True
            }
            
        except Exception as e:
            return {
                'error': f'카메라 시작 실패: {str(e)}',
                'success': False
            }
    
    def stop(self):
        """카메라 중지"""
        try:
            print("🛑 카메라 중지...")
            
            self.active = False
            self.detection_active = False
            
            if self.camera_manager and hasattr(self.camera_manager, 'stop_buffering'):
                self.camera_manager.detection_active = False
                self.camera_manager.stop_buffering()
                
            if self.camera:
                self.camera.release()
                
            return {
                'message': '카메라 중지됨',
                'status': 'stopped',
                'success': True
            }
            
        except Exception as e:
            return {
                'error': f'카메라 중지 실패: {str(e)}',
                'success': False
            }
    
    def get_status(self):
        """카메라 상태 확인"""
        camera_connected = (self.camera is not None and 
                           self.camera.isOpened() if self.camera else False)
        
        return {
            'streaming_active': self.active,
            'detection_active': self.detection_active,
            'camera_connected': camera_connected,
            'frame_count': self.frame_count,
            'camera_type': 'Raspberry Pi Camera' if CAMERA_MANAGER_AVAILABLE else 'Webcam',
            'latest_detection': get_latest_detection_result(),
            'timestamp': time.time(),
            'success': True
        }
    
    def get_frame(self):
        """프레임 획득 및 버퍼에 추가"""
        try:
            with self.lock:
                # 웹캠 시도 빈도를 줄여서 오류 메시지 감소
                if self.camera is None and self.frame_count % 100 == 0:  # 100프레임마다만 시도
                    try:
                        self.camera = cv2.VideoCapture(0)
                        if self.camera.isOpened():
                            print("✅ 웹캠 연결됨")
                            self.active = True
                            self._should_generate_dummy = False
                        else:
                            self.camera.release()
                            self.camera = None
                    except:
                        self.camera = None
                
                # 실제 카메라에서 프레임 읽기
                if self.camera is not None and self.camera.isOpened():
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        # VideoService에는 add_frame 메서드가 없으므로 제거
                        
                        self.frame_count += 1
                        self.latest_frame = frame.copy()
                        return frame
                    else:
                        # 카메라 연결 끊어짐
                        self.camera.release()
                        self.camera = None
                        self.active = False
                        self._should_generate_dummy = True
                        self._start_dummy_frame_generation()
                
                # 더미 프레임 반환
                if self.latest_frame is not None:
                    return self.latest_frame.copy()
                else:
                    return self._create_demo_frame(self.frame_count)
                
        except Exception as e:
            print(f"❌ 프레임 획득 실패: {e}")
            return self._create_demo_frame(self.frame_count)
    
    def mark_fall_detected(self):
        """낙상 감지 표시 (5초간 표시)"""
        self._last_detection_time = time.time()
    
    def generate_frames(self):
        """프레임 생성기"""
        print("📺 프레임 생성기 시작")
        
        while True:
            try:
                frame = self.get_frame()
                if frame is None:
                    # 대기 화면 표시
                    frame = self._create_waiting_frame()
                
                # JPEG 인코딩
                ret, buffer = cv2.imencode('.jpg', frame, [
                    cv2.IMWRITE_JPEG_QUALITY, 85
                ])
                
                if ret:
                    yield buffer.tobytes()
                
                time.sleep(0.033)  # ~30fps
                
            except Exception as e:
                print(f"❌ 프레임 생성 실패: {e}")
                time.sleep(0.1)
    
    def _create_waiting_frame(self):
        """대기 화면 생성"""
        waiting_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 배경 그라데이션
        for i in range(480):
            color_val = int(30 + (i / 480) * 50)
            waiting_frame[i, :] = [color_val, color_val, color_val]
        
        # 제목
        cv2.putText(waiting_frame, "SafeFall Camera System", (120, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # 상태 메시지
        cv2.putText(waiting_frame, "Waiting for camera connection...", (140, 250), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)
        
        # 시간 표시
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(waiting_frame, current_time, (200, 420), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return waiting_frame

class StreamState:
    """Fallback JPEG + helper"""
    def __init__(self):
        self.latest_jpeg = None
        self.latest_ts = 0
        self.lock = Lock()
        self.active_window = 10  # 10초 활성 윈도우
    
    def update_jpeg(self, jpeg_bytes):
        with self.lock:
            self.latest_jpeg = jpeg_bytes
            self.latest_ts = time.time()
    
    def get_latest(self):
        with self.lock:
            return self.latest_jpeg, self.latest_ts
    
    def fallback_recent(self):
        with self.lock:
            if not self.latest_jpeg: 
                return False
            return (time.time() - self.latest_ts) < self.active_window

# Base64로 인코딩된 빈 JPEG 이미지
BLANK_JPEG = base64.b64decode(
    b'/9j/4AAQSkZJRgABAQEASABIAAD/2wBDABALDA4MChAODQ4SERATGCgaGBgYGi0l'
    b'JC4tLzQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NP/2wBDARESEhURGCgY'
    b'GCg0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0NDQ0'
    b'NP/wAARCAAQABADASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEA'
    b'ABAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAwT/xAAUEQEAAA'
    b'AAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCfAAf/2Q=='
)

class StreamBuilder:
    def __init__(self, handler, stream_state):
        self.handler = handler
        self.stream_state = stream_state
    
    def build(self):
        try:
            gen = self.handler.get_video_stream()
        except Exception as e:
            print(f"[stream] primary error: {e}")
            gen = None
        
        if isinstance(gen, Response):
            return gen
        
        def primary_wrapper():
            for frame_bytes in gen:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
                       frame_bytes + b'\r\n')
        
        def fallback_wrapper():
            print("[stream] fallback generator")
            boundary = b'--frame'
            last_log = 0
            while True:
                jpeg, _ = self.stream_state.get_latest()
                if jpeg:
                    out = jpeg
                else:
                    out = BLANK_JPEG
                    now = time.time()
                    if now - last_log > 5:
                        print("[fallback] waiting first frame...")
                        last_log = now
                yield (boundary + b'\r\nContent-Type: image/jpeg\r\n\r\n' +
                       out + b'\r\n')
                time.sleep(0.06)
        
        if gen is not None:
            try:
                return Response(primary_wrapper(), mimetype='multipart/x-mixed-replace; boundary=frame')
            except Exception as e:
                print(f"[stream] primary fail -> fallback: {e}")
        
        return Response(fallback_wrapper(), mimetype='multipart/x-mixed-replace; boundary=frame')