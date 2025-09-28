import os
import sys
import threading
import cv2
import subprocess
import platform
import tempfile
import numpy as np
from queue import Queue
import time
import random

# torch는 선택적으로 import (라즈베리파이에서는 없어도 됨)
try:
    import torch
    TORCH_AVAILABLE = True
    print("✅ torch 사용 가능")
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️ torch 없음 - AI 기능 비활성화 (카메라만 사용)")

AUTH = f"Bearer {os.getenv('AUTH_TOKEN', '')}"

def authed(req):
    return req.headers.get("Authorization", "") == AUTH

_yolo_cache = {"flavor": None, "model": None, "names": None}
_lock = threading.Lock()

# 전역 감지 상태
latest_detection_result = {
    'fall_detected': False,
    'confidence': 0.0,
    'timestamp': None
}
simulation_mode = False
simulation_probability = 0.1
camera_manager = None

class CameraManager:
    """기본 카메라 관리 클래스"""
    def __init__(self):
        self.camera = None
        self.active = False
        self.buffering_active = False
        self.detection_active = False
        self.frame_queue = Queue(maxsize=10)
        self.thread = None
    
    def initialize_camera(self):
        """카메라 초기화 및 버퍼링 스레드 시작"""
        # ...existing code...
    
    def start_buffering(self):
        """영상 버퍼링 시작"""
        # ...existing code...
    
    def stop_buffering(self):
        """영상 버퍼링 중지"""
        # ...existing code...
    
    def release(self):
        """카메라 리소스 해제"""
        # ...existing code...

class RPiCamWrapper:
    """rpicam을 사용한 라즈베리파이 카메라 래퍼"""
    # ...existing code...

def detect_fall_in_frame(frame, model=None, names=None):
    """기본 낙상 감지 함수 (녹화 기능 없음)"""
    global latest_detection_result, simulation_mode
    
    # 시뮬레이션 모드인 경우 무작위로 낙상 감지 결과 생성
    if simulation_mode and random.random() < simulation_probability:
        result = {
            'fall_detected': True,
            'confidence': round(random.uniform(0.5, 1.0), 2),
            'bbox': [100, 100, 200, 200],  # 임의의 바운딩 박스
            'timestamp': time.time()
        }
        latest_detection_result = result
        return result
    
    # 실제 YOLO 모델을 사용한 감지
    # ...existing code...

def set_simulation_mode(enable):
    """시뮬레이션 모드 설정"""
    global simulation_mode
    simulation_mode = enable
    return simulation_mode

def get_latest_detection_result():
    """최신 감지 결과 반환"""
    return latest_detection_result

def get_camera_manager():
    """기본 카메라 매니저 인스턴스 반환"""
    global camera_manager
    if camera_manager is None:
        camera_manager = CameraManager()
    return camera_manager

def test_rpicam():
    """rpicam 명령어 테스트"""
    # ...existing code...

def _load_pure_weights():
    """순수 가중치 파일에서 로드 (fallback용)"""
    if not TORCH_AVAILABLE:
        return "v5", None, None, "torch_not_available"
    
    try:
        # 현재 back-end 폴더에서 모델 찾기
        base_dir = os.path.dirname(os.path.abspath(__file__))  # utils 폴더
        back_end_dir = os.path.dirname(base_dir)  # back-end 폴더
        
        # 여러 경로에서 best.pt 찾기
        model_paths = [
            os.path.join(back_end_dir, "best.pt"),  # back-end/best.pt
            os.path.join(back_end_dir, "models", "best.pt"),  # back-end/models/best.pt
            os.path.join(back_end_dir, "best_pure_weights.pt")  # 순수 가중치
        ]
        
        for model_path in model_paths:
            if os.path.exists(model_path):
                print(f"✅ Found model file: {model_path}")
                data = torch.load(model_path, map_location="cpu", weights_only=True)
                names = _normalize_names(data.get('names', {0: 'fall'}))
                
                class YOLOWrapper:
                    def __init__(self, names):
                        self.names = names
                    def __call__(self, x):
                        return x
                    def eval(self):
                        return self
                    def cpu(self):
                        return self
                    def float(self):
                        return self
                
                wrapper = YOLOWrapper(names)
                return "v5", wrapper, names, None
        
        print("❌ No model file found in any location")
        return "v5", None, None, "no_model_file"
        
    except Exception as e:
        print(f"❌ Model load failed: {e}")
        return "v5", None, None, f"model_load_failed: {e}"

def load_yolo_auto():
    """
    back-end 폴더에서 YOLOv5 모델 로드 (torch 선택적)
    """
    if not TORCH_AVAILABLE:
        print("⚠️ torch가 없어서 AI 모델을 로드할 수 없습니다.")
        return "none", None, None, "torch_not_available"
    
    with _lock:
        if _yolo_cache["model"] is not None:
            return _yolo_cache["flavor"], _yolo_cache["model"], _yolo_cache["names"], None

        print("YOLOv5 모델 로드 시작...")

        # back-end 폴더 기준으로 경로 설정
        utils_dir = os.path.dirname(os.path.abspath(__file__))  # utils 폴더
        back_end_dir = os.path.dirname(utils_dir)  # back-end 폴더
        
        # YOLOv5 경로가 있다면 추가
        yolo_path = os.path.join(back_end_dir, "yolov5")
        if os.path.exists(yolo_path):
            sys.path.insert(0, yolo_path)
            print(f"YOLOv5 경로 추가: {yolo_path}")
        
        try:
            # 실제 모델 로드 시도 - back-end 폴더에서
            model_paths = [
                os.path.join(back_end_dir, "best.pt"),  # back-end/best.pt
                os.path.join(back_end_dir, "models", "best.pt"),  # back-end/models/best.pt
            ]
            
            for model_path in model_paths:
                if os.path.exists(model_path):
                    print(f"✅ 모델 파일 발견: {model_path}")
                    
                    try:
                        # YOLOv5 환경에서 모델 로드
                        checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
                        model = checkpoint.get('model', checkpoint)  # 호환성
                        names = checkpoint.get('names', {0: 'fall'})
                        
                        # 모델 설정
                        model = model.float().cpu().eval()
                        names = _normalize_names(names)
                        
                        # 캐시에 저장
                        _yolo_cache.update(flavor="v5", model=model, names=names)
                        
                        print("SUCCESS: YOLOv5 모델 로드 완료!")
                        print(f"모델 타입: {type(model)}")
                        print(f"클래스: {names}")
                        
                        return "v5", model, names, None
                        
                    except Exception as load_error:
                        print(f"모델 로드 실패: {load_error}")
                        continue
            
            # YOLOv8 시도
            print("YOLOv5 실패, Ultralytics YOLOv8 시도...")
            try:
                from ultralytics import YOLO
                
                for model_path in model_paths:
                    if os.path.exists(model_path):
                        model = YOLO(model_path)
                        names = {0: 'fall'}
                        
                        _yolo_cache.update(flavor="v8", model=model, names=names)
                        print("SUCCESS: YOLOv8 모델 로드 완료!")
                        return "v8", model, names, None
                        
            except Exception as e2:
                print(f"YOLOv8도 실패: {e2}")
                
        except Exception as e:
            print(f"모델 로드 중 오류: {e}")
        
        # 모든 방법 실패 시 fallback
        print("모든 모델 로드 실패, fallback 사용...")
        return _load_pure_weights()

# ...existing code...