"""전역 프레임 저장소 모듈"""
import threading

# 전역 변수들
latest_camera_frame = None
frame_lock = threading.Lock()

def set_frame(frame):
    """프레임 설정"""
    global latest_camera_frame, frame_lock
    with frame_lock:
        latest_camera_frame = frame.copy() if frame is not None else None

def get_frame():
    """프레임 가져오기"""
    global latest_camera_frame, frame_lock
    with frame_lock:
        if latest_camera_frame is not None:
            return latest_camera_frame.copy()
        return None

def has_frame():
    """프레임이 있는지 확인"""
    global latest_camera_frame, frame_lock
    with frame_lock:
        return latest_camera_frame is not None
