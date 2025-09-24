# detection/infer.py
from ultralytics import YOLO
from PIL import Image
import io, os, tempfile

def load_yolo_v8(weights_path: str):
    model = YOLO(weights_path)  # 예: /srv/flaskapp/best.pt
    names = model.names
    if isinstance(names, list):
        names = {i: n for i, n in enumerate(names)}
    return model, names

def infer_with_v8_model(model, image_bytes, class_names=None, imgsz=640, device="cpu"):
    """
    YOLOv8 추론 (항상 파일 경로 기반)
    """
    # 1) 바이트 → 임시 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        # 2) YOLOv8 예측
        results = model.predict(
            source=tmp_path,
            conf=0.25,
            iou=0.45,
            device=device,
            imgsz=imgsz,
            verbose=False,
        )

        dets = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()

                if isinstance(class_names, dict):
                    label = class_names.get(cls_id, str(cls_id))
                elif isinstance(class_names, (list, tuple)) and 0 <= cls_id < len(class_names):
                    label = class_names[cls_id]
                else:
                    label = str(cls_id)

                dets.append({
                    "cls": cls_id,
                    "label": label,
                    "conf": conf,
                    "xyxy": xyxy,
                })

        return dets
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
