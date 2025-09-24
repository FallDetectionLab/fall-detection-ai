# sf_models/yolo.py
"""
YOLOv5 DetectionModel wrapper for safe unpickling
"""
import sys
import os

# YOLOv5 경로 추가 (import 전에)
yolov5_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'yolov5')
if os.path.isdir(yolov5_path) and yolov5_path not in sys.path:
    sys.path.append(yolov5_path)

try:
    from models.yolo import DetectionModel as OriginalDetectionModel
    
    class DetectionModel(OriginalDetectionModel):
        """Safe wrapper for YOLOv5 DetectionModel"""
        pass

except ImportError as e:
    print(f"Warning: Could not import YOLOv5 DetectionModel: {e}")
    
    # Fallback: 기본 클래스 정의
    import torch.nn as nn
    
    class DetectionModel(nn.Module):
        """Fallback DetectionModel for safe unpickling"""
        def __init__(self, *args, **kwargs):
            super().__init__()
            print("Warning: Using fallback DetectionModel")
        
        def forward(self, x):
            return x
