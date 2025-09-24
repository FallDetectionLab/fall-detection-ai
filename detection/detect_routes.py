# detection/detect_routes.py
import os
import sys
import urllib.request
import traceback
import subprocess
from datetime import datetime, timezone

import boto3
from botocore.config import Config as BotoCfg
from flask import Blueprint, request

from utils.app_utils import authed, clear_model_cache
from detection.infer import load_yolo_v8, infer_with_v8_model
from services.notification_service import create_notification

detect_bp = Blueprint("detect", __name__)

# =========================
# 환경 설정
# =========================
S3_BUCKET = os.getenv("S3_BUCKET", "safefall2").strip()
S3_REGION = os.getenv("AWS_REGION", "ap-northeast-2").strip()
YOLO_WEIGHTS = os.getenv("YOLO_WEIGHTS", "/srv/flaskapp/best.pt")

# DVR → 클립 업로더 스크립트 경로 및 파라미터
CLIP_UPLOADER = os.getenv("CLIP_UPLOADER", "/usr/local/bin/safefall-clip-upload.sh")
CLIP_BEFORE_SEC = int(os.getenv("CLIP_BEFORE_SEC", "30"))  # 이벤트 이전 초
CLIP_AFTER_SEC = int(os.getenv("CLIP_AFTER_SEC", "30"))    # 이벤트 이후 초

# 백엔드 프로세스 환경에 AUTH_TOKEN이 없다면 기본값 (systemd에서 Environment로 넣는 걸 권장)
os.environ.setdefault("AUTH_TOKEN", os.getenv("AUTH_TOKEN", "test-token"))
# EC2 메타데이터 비활성화(컨테이너/EC2 외 환경 대비)
os.environ["AWS_EC2_METADATA_DISABLED"] = os.getenv("AWS_EC2_METADATA_DISABLED", "false")

# S3 client
_s3 = boto3.client(
    "s3",
    region_name=S3_REGION,
    config=BotoCfg(signature_version="s3v4", retries={"max_attempts": 2, "mode": "standard"})
)


# =========================
# 입력 이미지 바이트 확보
# =========================
def _get_image_bytes():
    """
    1) multipart/form-data: 'image' 파일
    2) JSON: { "s3_key": "..." }  -> S3 get_object
    3) JSON: { "s3_url": "..." }  -> presigned/public URL fetch
    """
    f = request.files.get("image")
    if f:
        return f.read(), None

    data = request.get_json(silent=True) or {}
    if not data:
        return None, "no_image"

    s3_key = data.get("s3_key")
    if s3_key:
        try:
            obj = _s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
            return obj["Body"].read(), None
        except Exception as e:
            return None, f"s3_get_error:{e}"

    s3_url = data.get("s3_url")
    if s3_url:
        try:
            with urllib.request.urlopen(s3_url, timeout=5) as r:
                return r.read(), None
        except Exception as e:
            return None, f"url_fetch_error:{e}"

    return None, "no_image"


# =========================
# DVR 클립 추출/업로드 트리거
# =========================
def _trigger_clip_uploader(event_time_utc: datetime, before_s: int, after_s: int):
    """
    비동기 백그라운드로 /usr/local/bin/safefall-clip-upload.sh 실행.
    인자:
      - event_time_utc: UTC naive/aware 모두 허용, 내부에서 ISO8601Z로 변환
      - before_s, after_s: 앞/뒤 길이(초)
    """
    if event_time_utc.tzinfo is None:
        event_time_utc = event_time_utc.replace(tzinfo=timezone.utc)
    iso_z = event_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    cmd = [CLIP_UPLOADER, iso_z, str(before_s), str(after_s)]
    env = os.environ.copy()  # AUTH_TOKEN 등 전달
    try:
        subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, None
    except Exception as e:
        return False, str(e)


# =========================
# /detect
# =========================
@detect_bp.post("/detect")
def detect_auto():
    if not authed(request):
        return {"ok": False, "error": "unauthorized"}, 401

    # 입력 이미지 확보
    img_bytes, err = _get_image_bytes()
    if err:
        return {"ok": False, "error": err}, 400

    # YOLOv8 모델 로드
    try:
        model, names = load_yolo_v8(YOLO_WEIGHTS)
    except Exception as e:
        return {"ok": False, "error": f"load_failed:{e}"}, 503

    # 추론 수행
    try:
        dets = infer_with_v8_model(
            model=model,
            image_bytes=img_bytes,
            class_names=names,
            imgsz=640,
            device="cpu"
        )

        # 라벨 보정: 'item' -> 'fall' (학습 레이블 보정용)
        for det in dets:
            if det.get("label") == "item":
                det["label"] = "fall"

        # 낙상 판단 + 알림 + 클립 트리거
        fire_notification = False
        highest_conf = 0.0
        clip_triggered = False
        clip_error = None

        for det in dets:
            lbl = det.get("label")
            conf = float(det.get("conf", 0.0))
            highest_conf = max(highest_conf, conf)

            if lbl == "fall" and conf > 0.4:
                # 1) 알림
                fire_notification = True
                confidence_percent = conf * 100.0
                create_notification(
                    title="🚨 낙상 감지 알림",
                    message=f"신뢰도 {confidence_percent:.1f}%로 낙상이 감지되었습니다. 즉시 확인이 필요합니다.",
                    notification_type="fall_detected",
                    severity="high"
                )

                # 2) DVR에서 ±N초 클립 추출/업로드 비동기 트리거
                #    NOTE: 지금은 서버 now 기준. (실전에서는 프레임 timestamp 사용 권장)
                now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
                clip_triggered, clip_error = _trigger_clip_uploader(
                    now_utc, CLIP_BEFORE_SEC, CLIP_AFTER_SEC
                )
                break  # 한 번만 트리거

        return {
            "ok": True,
            "flavor": "v8",
            "detections": dets,
            "summary": {
                "max_conf": highest_conf,
                "notified": fire_notification,
                "clip_triggered": clip_triggered,
                "clip_error": clip_error
            }
        }, 200

    except Exception as e:
        return {
            "ok": False,
            "flavor": "v8",
            "error": f"infer_error:{e}",
            "trace": traceback.format_exc(limit=2)
        }, 500
