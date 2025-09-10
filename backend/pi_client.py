#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspberry Pi/Mac client (direct upload to Flask)
- Every N seconds: capture JPEG frame -> POST /ingest/frame (multipart)
- On detection hook (demo): record N-sec clip -> POST /ingest/clip (multipart)
"""
import os, time, json, uuid, base64, subprocess, datetime as dt, platform
import cv2, requests

# ====== CONFIG ======
DEVICE_ID = os.getenv("DEVICE_ID", "pi-01")
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:5000")  # Flask 서버 주소
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
AUTH_HEADER = {"Authorization": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else {}

FRAME_INTERVAL_SEC = int(os.getenv("FRAME_INTERVAL_SEC", "2"))
FRAME_QUALITY = int(os.getenv("FRAME_QUALITY", "90"))
CLIP_DURATION = int(os.getenv("CLIP_DURATION", "5"))

HOME = os.path.expanduser("~")
OUT_DIR = os.getenv("OUT_DIR", os.path.join(HOME, "safefall", "out"))
QUEUE_DIR = os.path.join(OUT_DIR, "queue")
CLIPS_DIR = os.path.join(OUT_DIR, "clips")
os.makedirs(QUEUE_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)
# =====================


def now_utc_str():
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_frame_direct(jpg_bytes: bytes, device_id: str):
    url = f"{API_BASE}/ingest/frame"
    files = {"frame": ("frame.jpg", jpg_bytes, "image/jpeg")}
    data = {"device_id": device_id, "ts": str(time.time())}
    r = requests.post(url, files=files, data=data, headers=AUTH_HEADER, timeout=10)
    if r.status_code // 100 != 2:
        print("[WARN] ingest_frame fail:", r.status_code, r.text[:200])
        return False
    return True


def upload_clip_direct(mp4_path: str, device_id: str):
    url = f"{API_BASE}/ingest/clip"
    with open(mp4_path, "rb") as f:
        files = {"clip": ("clip.mp4", f, "video/mp4")}
        data = {"device_id": device_id, "ts": str(time.time())}
        r = requests.post(url, files=files, data=data, headers=AUTH_HEADER, timeout=60)
    if r.status_code // 100 != 2:
        print("[WARN] ingest_clip fail:", r.status_code, r.text[:200])
        return False
    return True


IS_MAC = platform.system() == "Darwin"


def record_clip(seconds=5):
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
            "0",
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
            "/dev/video0",
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


def dummy_detection_condition(frame):
    # 아주 단순한 데모: 화면 평균 밝기 낮으면 이벤트
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(gray.mean()) < 35.0


def main():
    cap = cv2.VideoCapture(0)  # Pi: /dev/video0, Mac: 카메라 0
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    last_frame_ts = 0.0
    cooldown_until = 0.0

    # 실행 직후 1회 테스트 클립 생성(보고 확인 용도)
    event_id, path = record_clip(CLIP_DURATION)
    print("[DEBUG] forced clip:", event_id, path)
    if event_id and path:
        upload_clip_direct(path, DEVICE_ID)

    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.2)
            continue

        now = time.time()
        # 1) 주기 프레임 업로드
        if now - last_frame_ts >= FRAME_INTERVAL_SEC:
            last_frame_ts = now
            # JPEG 인코딩
            res, buf = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, FRAME_QUALITY]
            )
            if res:
                upload_frame_direct(buf.tobytes(), DEVICE_ID)

        # 2) 임시 감지 훅 → 클립 업로드
        try:
            if now >= cooldown_until and dummy_detection_condition(frame):
                print("[INFO] detection trigger -> record clip")
                eid, clip_path = record_clip(CLIP_DURATION)
                if eid and clip_path:
                    upload_clip_direct(clip_path, DEVICE_ID)
                cooldown_until = now + 60.0  # 60초 쿨다운
        except Exception as e:
            print(f"[WARN] detection flow error: {e}")

        time.sleep(0.05)


if __name__ == "__main__":
    main()
