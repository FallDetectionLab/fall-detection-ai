#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SafeFall Raspberry Pi/Mac client
- Pi: rpicam-still / rpicam-vid 사용
- Mac: ffmpeg fallback
- Presigned URL로 S3 업로드 + /events 호출
"""

import os, time, json, uuid, base64, subprocess, shutil, platform
import datetime as dt
import urllib.request
import requests

# ============== ENV ==============
DEVICE_ID = os.getenv("DEVICE_ID", "pi-01")
API_BASE = os.getenv("API_BASE", "http://web-alb-1848254395.ap-northeast-2.elb.amazonaws.com")  # EC2 ALB DNS로 교체
AUTH = f"Bearer {os.getenv('AUTH_TOKEN','')}"
FRAME_INTERVAL_SEC = int(os.getenv("FRAME_INTERVAL_SEC", "2"))
FRAME_QUALITY = int(os.getenv("FRAME_QUALITY", "90"))
CLIP_DURATION = int(os.getenv("CLIP_DURATION", "10"))

HOME = os.path.expanduser("~")
OUT_DIR = os.getenv("OUT_DIR", os.path.join(HOME, "safefall", "out"))
QUEUE_DIR = os.path.join(OUT_DIR, "queue")
CLIPS_DIR = os.path.join(OUT_DIR, "clips")

# ============== PLATFORM DETECT ==============
RPICAM_STILL = shutil.which("rpicam-still")
RPICAM_VID = shutil.which("rpicam-vid")
IS_PI_RPICAM = bool(RPICAM_STILL and RPICAM_VID)
IS_MAC = platform.system() == "Darwin"

# ============== UTIL ==============
def now_utc_iso():
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def ensure_dirs():
    for d in [OUT_DIR, QUEUE_DIR, CLIPS_DIR]:
        os.makedirs(d, exist_ok=True)

# ============== SERVER CALLS ==============
def presign(key: str, content_type: str):
    url = f"{API_BASE}/media/presign"
    r = requests.post(url, json={"key": key, "content_type": content_type},
                      headers={"Authorization": AUTH}, timeout=10)
    r.raise_for_status()
    return r.json()

def http_put(upload_url: str, headers: dict, data: bytes):
    req = urllib.request.Request(upload_url, data=data, method="PUT")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as _:
        return True
    return False

def post_event(payload: dict):
    url = f"{API_BASE}/events"
    r = requests.post(url, json=payload, headers={"Authorization": AUTH}, timeout=10)
    return r.status_code // 100 == 2

# ============== CAPTURE ==============
def capture_frame_bytes_rpicam(width=1280, height=720, quality=90):
    cmd = [RPICAM_STILL, "-o", "-", "-n", "--width", str(width), "--height", str(height),
           "--quality", str(quality), "--timeout", "1"]
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    except:
        return None

def capture_frame_bytes_mac(width=1280, height=720):
    tmp_path = os.path.join(OUT_DIR, "tmp_frame.jpg")
    cmd = ["ffmpeg", "-y", "-f", "avfoundation", "-framerate", "30",
           "-video_size", f"{width}x{height}", "-i", "0", "-vframes", "1",
           "-q:v", "2", tmp_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(tmp_path, "rb") as f:
            return f.read()
    except:
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def upload_frame_once():
    if IS_PI_RPICAM:
        data = capture_frame_bytes_rpicam(quality=FRAME_QUALITY)
    elif IS_MAC:
        data = capture_frame_bytes_mac()
    else:
        print("[WARN] Unknown platform")
        return

    if not data:
        return

    key = f"frames/{DEVICE_ID}/{dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
    p = presign(key, "image/jpeg")
    http_put(p["upload_url"], p.get("headers", {}), data)
    post_event({
        "device_id": DEVICE_ID,
        "type": "frame",
        "captured_at": now_utc_iso(),
        "media": [{"kind": "frame", "key": key}]
    })

# ============== MAIN LOOP ==============
def main():
    print(f"[BOOT] DEVICE_ID={DEVICE_ID} API_BASE={API_BASE}")
    ensure_dirs()

    last_frame_ts = 0.0
    while True:
        now = time.time()
        if now - last_frame_ts >= FRAME_INTERVAL_SEC:
            last_frame_ts = now
            upload_frame_once()
        time.sleep(0.05)

if __name__ == "__main__":
    main()
