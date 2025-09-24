# utils/app_utils.py - 경로 강제 설정 버전
import os
import sys
import threading
import torch

AUTH = f"Bearer {os.getenv('AUTH_TOKEN', '')}"

def authed(req):
    return req.headers.get("Authorization", "") == AUTH

_yolo_cache = {"flavor": None, "model": None, "names": None}
_lock = threading.Lock()

def _normalize_names(names):
    if isinstance(names, list):
        return {i: n for i, n in enumerate(names)}
    if isinstance(names, dict):
        return names
    return {}

def clear_model_cache():
    with _lock:
        _yolo_cache.update(flavor=None, model=None, names=None)

def _load_pure_weights():
    """순수 가중치 파일에서 로드 (fallback용)"""
    try:
        pure_weights = "/srv/flaskapp/best_pure_weights.pt"
        if os.path.exists(pure_weights):
            data = torch.load(pure_weights, map_location="cpu", weights_only=True)
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
        else:
            return "v5", None, None, "no_pure_weights_file"
    except Exception as e:
        return "v5", None, None, f"pure_weights_failed: {e}"

def load_yolo_auto():
    """
    강제 경로 설정으로 실제 YOLOv5 모델 로드
    """
    with _lock:
        if _yolo_cache["model"] is not None:
            return _yolo_cache["flavor"], _yolo_cache["model"], _yolo_cache["names"], None

        print("YOLOv5 모델 로드 시작...")

        # 강제 경로 설정
        yolo_path = "/srv/flaskapp/yolov5"
        original_cwd = os.getcwd()
        
        # 기존 경로들 제거 후 맨 앞에 추가
        paths_to_remove = [p for p in sys.path if 'yolov5' in p]
        for p in paths_to_remove:
            while p in sys.path:
                sys.path.remove(p)
        
        sys.path.insert(0, yolo_path)
        print(f"경로 설정됨: {yolo_path}")
        
        # 작업 디렉토리 변경
        if os.path.isdir(yolo_path):
            os.chdir(yolo_path)
            print(f"작업 디렉토리 변경: {os.getcwd()}")
        
        try:
            # 실제 모델 로드 시도
            real_model_path = "/srv/flaskapp/best_real_model.pt"
            if os.path.exists(real_model_path):
                print("실제 모델 파일 발견, 로드 중...")
                
                # YOLOv5 환경에서 모델 로드
                data = torch.load(real_model_path, map_location="cpu", weights_only=False)
                model = data['model']
                names = data.get('names', {0: 'fall'})
                
                # 모델 설정
                model = model.float().cpu().eval()
                names = _normalize_names(names)
                
                # 캐시에 저장
                _yolo_cache.update(flavor="v5", model=model, names=names)
                
                print("SUCCESS: 실제 YOLOv5 모델 로드 완료!")
                print(f"모델 타입: {type(model)}")
                print(f"클래스: {names}")
                
                return "v5", model, names, None
            else:
                print("실제 모델 파일이 없음, 원본 모델 로드 시도...")
                
                # 원본 best.pt 로드 시도
                original_model_path = "/srv/flaskapp/best.pt"
                checkpoint = torch.load(original_model_path, map_location="cpu", weights_only=False)
                model = checkpoint['model']
                names = checkpoint.get('names', {0: 'fall'})
                
                model = model.float().cpu().eval()
                names = _normalize_names(names)
                
                _yolo_cache.update(flavor="v5", model=model, names=names)
                
                print("SUCCESS: 원본 YOLOv5 모델 로드 완료!")
                print(f"모델 타입: {type(model)}")
                print(f"클래스: {names}")
                
                return "v5", model, names, None
                
        except Exception as e:
            print(f"실제 모델 로드 실패: {e}")
            print("Ultralytics YOLOv8 시도...")
            
            # YOLOv8 시도
            try:
                from ultralytics import YOLO
                model = YOLO("/srv/flaskapp/best.pt")
                names = {0: 'fall'}
                
                _yolo_cache.update(flavor="v8", model=model, names=names)
                print("SUCCESS: YOLOv8 모델 로드 완료!")
                return "v8", model, names, None
                
            except Exception as e2:
                print(f"YOLOv8도 실패: {e2}")
                print("Fallback 모드로 전환...")
                
        finally:
            # 작업 디렉토리 복원
            os.chdir(original_cwd)
        
        # 모든 방법 실패 시 fallback
        print("모든 실제 모델 로드 실패, fallback 사용...")
        return _load_pure_weights()
