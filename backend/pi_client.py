#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspberry Pi client (frames + clip upload via presigned URL, event POST)
- Every N seconds: capture JPEG frame and upload to S3 via presigned URL
- On detection hook: record 10s clip (ffmpeg) -> upload -> POST /events
"""
import os, time, json, uuid, base64, subprocess, datetime as dt
import cv2, urllib.request, urllib.error, urllib.parse, requests

# ====== CONFIG ======
DEVICE_ID = os.getenv("DEVICE_ID", "pi-01")
API_BASE = os.getenv("API_BASE", "https://<YOUR-API-DOMAIN>")  # Flask 서버 도메인
FRAME_INTERVAL_SEC = int(os.getenv("FRAME_INTERVAL_SEC", "2"))  # 2초마다 프레임
FRAME_QUALITY = int(os.getenv("FRAME_QUALITY", "90"))  # JPEG 품질
CLIP_DURATION = int(os.getenv("CLIP_DURATION", "10"))  # 이벤트 클립 길이(초)
HOME = os.path.expanduser("~")
OUT_DIR = os.getenv("OUT_DIR", os.path.join(HOME, "safefall", "out"))
QUEUE_DIR = os.path.join(OUT_DIR, "queue")
CLIPS_DIR = os.path.join(OUT_DIR, "clips")
# =====================


def now_utc_str():
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def ts_path_parts():
    now = dt.datetime.utcnow()
    return now.strftime("%Y/%m/%d"), now.strftime("%H%M%S")


def ensure_dirs():
    for d in [OUT_DIR, QUEUE_DIR, CLIPS_DIR]:
        os.makedirs(d, exist_ok=True)


def presign(key: str, content_type: str):
    """POST /media/presign -> { upload_url, headers, public_url }"""
    url = f"{API_BASE}/media/presign"
    r = requests.post(url, json={"key": key, "content_type": content_type}, timeout=10)
    r.raise_for_status()
    return r.json()


def http_put(upload_url: str, headers: dict, data: bytes, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(upload_url, data=data, method="PUT")
            for k, v in (headers or {}).items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=20) as _:
                return True
        except Exception as e:
            if i == retries - 1:
                print(f"[ERROR] PUT failed: {e}")
                return False
            time.sleep(1.5 * (i + 1))


def post_event(payload: dict, retries=3):
    url = f"{API_BASE}/events"
    for i in range(retries):
        try:
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code // 100 == 2:
                return True
            print(f"[WARN] /events status {r.status_code}: {r.text[:120]}")
        except Exception as e:
            print(f"[WARN] /events error: {e}")
        time.sleep(1.5 * (i + 1))
    return False


def save_to_queue(item: dict):
    """디스크 큐에 남겼다가 나중에 재시도"""
    name = f"{dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.json"
    path = os.path.join(QUEUE_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False)
    print(f"[QUEUE] saved: {path}")


def process_queue():
    """큐에 쌓인 업로드/이벤트 재시도"""
    files = sorted([f for f in os.listdir(QUEUE_DIR) if f.endswith(".json")])
    for fn in files[:10]:  # 한 번에 너무 많이 처리하지 않게
        path = os.path.join(QUEUE_DIR, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                item = json.load(f)
            ok = False
            if item["type"] == "put":
                ok = http_put(
                    item["upload_url"],
                    item.get("headers", {}),
                    base64.b64decode(item["data_b64"]),
                )
            elif item["type"] == "event":
                ok = post_event(item["payload"])
            if ok:
                os.remove(path)
                print(f"[QUEUE] done & removed: {fn}")
        except Exception as e:
            print(f"[QUEUE] error {fn}: {e}")


def capture_and_upload_frame(cap):
    ok, frame = cap.read()
    if not ok:
        print("[WARN] camera read fail")
        return

    # JPEG 인코딩
    res, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, FRAME_QUALITY])
    if not res:
        print("[WARN] jpeg encode fail")
        return
    data = buf.tobytes()

    # S3 key
    date_path, hms = ts_path_parts()
    key = f"frames/{DEVICE_ID}/{date_path}/{hms}.jpg"

    # presign -> PUT
    try:
        p = presign(key, "image/jpeg")
        ok = http_put(p["upload_url"], p.get("headers", {}), data)
        if not ok:
            save_to_queue(
                {
                    "type": "put",
                    "upload_url": p["upload_url"],
                    "headers": p.get("headers", {}),
                    "data_b64": base64.b64encode(data).decode("ascii"),
                }
            )
        else:
            # (선택) 프레임도 /events 로깅
            post_event(
                {
                    "device_id": DEVICE_ID,
                    "type": "frame",
                    "captured_at": now_utc_str(),
                    "confidence": None,
                    "bbox": None,
                    "media": [{"kind": "frame", "key": key}],
                }
            )
    except Exception as e:
        print(f"[WARN] frame upload error: {e}")


import platform

IS_MAC = platform.system() == "Darwin"


def record_clip(seconds=10):
    event_id = f"evt_{dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    out_path = os.path.join(CLIPS_DIR, f"{event_id}.mp4")

    if IS_MAC:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "avfoundation",
            "-framerate",
            "30",
            "-video_size",
            "1280x720",
            "-i",
            "0",  # ← 맥 카메라 0번
            "-t",
            str(seconds),
            "-vcodec",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            out_path,
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "v4l2",
            "-framerate",
            "15",
            "-video_size",
            "1280x720",
            "-i",
            "/dev/video0",  # ← 라즈베리파이/리눅스
            "-t",
            str(seconds),
            "-vcodec",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            out_path,
        ]

    try:
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return event_id, out_path
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] ffmpeg clip failed: {e}")
        return None, None


def upload_clip_and_event(event_id, clip_path, confidence=0.8, bbox=None):
    # presign -> PUT
    date_path, _ = ts_path_parts()
    key = f"clips/{DEVICE_ID}/{date_path}/{event_id}.mp4"
    try:
        with open(clip_path, "rb") as f:
            data = f.read()
        p = presign(key, "video/mp4")
        ok = http_put(p["upload_url"], p.get("headers", {}), data)
        if not ok:
            save_to_queue(
                {
                    "type": "put",
                    "upload_url": p["upload_url"],
                    "headers": p.get("headers", {}),
                    "data_b64": base64.b64encode(data).decode("ascii"),
                }
            )
        # /events
        ev_payload = {
            "device_id": DEVICE_ID,
            "type": "fall",
            "captured_at": now_utc_str(),
            "confidence": confidence,
            "bbox": bbox or None,
            "media": [{"kind": "clip", "key": key}],
        }
        if not post_event(ev_payload):
            save_to_queue({"type": "event", "payload": ev_payload})
    except Exception as e:
        print(f"[WARN] clip upload/event error: {e}")


def dummy_detection_condition(frame):
    """임시 감지 훅: 밝기 평균이 특정 임계 넘으면 이벤트 라고 가정 (나중에 YOLO로 교체)"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    m = float(gray.mean())
    return m < 35.0  # 예: 너무 어두우면 이벤트로


def main():
    ensure_dirs()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    last_frame_ts = 0.0
    cooldown_until = 0.0  # 이벤트 쿨다운(중복 억제)

    # 👉 임시: 실행 직후 1회 클립 생성
    event_id, path = record_clip(CLIP_DURATION)
    print("[DEBUG] forced clip:", event_id, path)
    # (여기서 업로드/이벤트는 기존 루틴이 돌면서 처리되도록 그냥 두면 돼)

    while True:
        # 큐 재시도 (비용 작은 작업)
        process_queue()

        ok, frame = cap.read()
        if not ok:
            time.sleep(0.5)
            continue

        now = time.time()

        # 1) N초마다 프레임 업로드
        if now - last_frame_ts >= FRAME_INTERVAL_SEC:
            last_frame_ts = now
            capture_and_upload_frame(
                cap
            )  # 내부에서 다시 read하지 않고 이미 읽은 frame 쓰고 싶다면 구조 약간 수정

        # 2) 임시 감지 훅 (나중에 YOLO로 교체)
        try:
            if now >= cooldown_until and dummy_detection_condition(frame):
                print("[INFO] detection trigger -> record clip")
                event_id, clip_path = record_clip(CLIP_DURATION)
                if event_id:
                    upload_clip_and_event(
                        event_id, clip_path, confidence=0.85, bbox=None
                    )
                cooldown_until = now + 60.0  # 60초 쿨다운
        except Exception as e:
            print(f"[WARN] detection flow error: {e}")

        time.sleep(0.05)  # CPU 쉬게


if __name__ == "__main__":
    main()
