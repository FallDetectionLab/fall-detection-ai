"""
Raspberry Pi Camera Client (rpicam only)
Real-time frame capture and transmission to SafeFall backend.
"""

import os, sys, time, json, argparse, subprocess, threading, queue, signal, math, uuid
import requests
import numpy as np
import cv2

# 구성
DEFAULT_SERVER = os.getenv("SAFEFALL_SERVER", "http://172.16.52.76:5000")
DEFAULT_DEVICE = os.getenv("SAFEFALL_DEVICE_ID", "raspberry_pi_camera")
DEFAULT_SEND_FPS = float(os.getenv("SAFEFALL_SEND_FPS", "10"))
LOW_BW_ENV = os.getenv("SAFEFALL_LOW_BW", "0") == "1"

# 카메라 설정
CAP_WIDTH = 640
CAP_HEIGHT = 480
CAP_FPS = 30

# 큐 및 전송 설정
QUEUE_MAX = 30
WARMUP_BURST_SECONDS = 3.0
WARMUP_BURST_FPS = 15.0
REQUEST_TIMEOUT = 5
MAX_BACKOFF = 5.0
CONSEC_FAIL_RESTART = 20
CONSEC_FAIL_PREFLIGHT = 35
LOW_BW_TRIGGER = 8
LOW_BW_RES = (426, 240)
PING_INTERVAL = 30

def log(msg):
    print(f"[PiClient] {msg}")

def short_uuid():
    return uuid.uuid4().hex[:8]

class RaspberryPiCameraClient:
    def __init__(self, server_url=DEFAULT_SERVER, device_id=DEFAULT_DEVICE,
                 send_fps=DEFAULT_SEND_FPS, low_bw=False):
        self.server_url = server_url.rstrip("/")
        self.device_id = device_id
        self.target_send_fps = max(2.0, min(20.0, send_fps))
        self.session = requests.Session()

        self.rpicam_process = None
        self.active = False
        self.frame_queue = queue.Queue(maxsize=QUEUE_MAX)
        self.capture_thread = None
        self.send_thread = None
        self.health_thread = None
        self.ping_thread = None

        self._stop_event = threading.Event()
        self._last_send_monotonic = 0.0
        self._frame_counter = 0
        self._net_fail_count = 0
        self._burst_end_time = 0.0

        self.low_bw_mode = low_bw or LOW_BW_ENV
        self.current_width = CAP_WIDTH
        self.current_height = CAP_HEIGHT
        self.current_cap_fps = CAP_FPS
        self.last_fail_reason = ""
        self.last_preflight_ok = True

        log(f"Init: server={self.server_url} device={self.device_id} send_fps={self.target_send_fps} low_bw={self.low_bw_mode}")

        if server_url == "http://192.168.0.23:5000":
            log("⚠️ 기본 하드코딩 주소 사용 중 (SAFEEFALL_SERVER / --server 로 실제 IP 지정 권장)")

    # ----- rpicam 관리 -----
    def check_rpicam(self):
        try:
            r = subprocess.run(['rpicam-vid','--version'], capture_output=True,
                               text=True, timeout=5)
            if r.returncode == 0:
                log(f"rpicam-vid OK: {r.stdout.strip()}")
                return True
            log(f"rpicam-vid failed code={r.returncode}")
            return False
        except Exception as e:
            log(f"rpicam-vid check error: {e}")
            return False

    def list_cameras(self):
        try:
            r = subprocess.run(['rpicam-vid','--list-cameras'], capture_output=True,
                               text=True, timeout=8)
            if r.returncode == 0:
                log("Camera list:\n" + r.stdout.strip())
                return True
            log("Camera list failed")
            return False
        except Exception as e:
            log(f"Camera list error: {e}")
            return False

    def start_rpicam_stream(self):
        try:
            if self.low_bw_mode:
                self.current_width, self.current_height = LOW_BW_RES
                self.current_cap_fps = 20
            else:
                self.current_width, self.current_height = CAP_WIDTH, CAP_HEIGHT
                self.current_cap_fps = CAP_FPS
            cmd = [
                'rpicam-vid',
                '--camera','0',
                '--width', str(self.current_width),
                '--height', str(self.current_height),
                '--framerate', str(self.current_cap_fps),
                '--timeout','0',
                '--codec','mjpeg',
                '--output','-',
                '--inline',
                '--flush'
            ]
            log(f"Starting rpicam-vid (w={self.current_width} h={self.current_height} cap_fps={self.current_cap_fps} low_bw={self.low_bw_mode})...")
            self.rpicam_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            log("rpicam-vid started (PID={})".format(self.rpicam_process.pid))
            return True
        except Exception as e:
            log(f"rpicam start failed: {e}")
            return False

    # ----- 시작 / 중지 -----
    def start(self):
        if not self.check_rpicam():
            log("rpicam-vid not available.")
            return False
        self.list_cameras()
        if not self.start_rpicam_stream():
            return False

        self.active = True
        self._burst_end_time = time.monotonic() + WARMUP_BURST_SECONDS

        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.send_thread.start()

        self.health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self.health_thread.start()

        if PING_INTERVAL > 0:
            self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
            self.ping_thread.start()

        log("Streaming started")
        return True

    def stop(self):
        log("Stopping client...")
        self.active = False
        self._stop_event.set()

        if self.rpicam_process:
            try:
                self.rpicam_process.terminate()
                self.rpicam_process.wait(timeout=5)
                log("rpicam-vid terminated")
            except Exception:
                self.rpicam_process.kill()
                log("rpicam-vid force killed")

        for th in [self.capture_thread, self.send_thread, self.health_thread, self.ping_thread]:
            if th and th.is_alive():
                th.join(timeout=2)

        log("Stopped")

    # ----- 캡처 루프 -----
    def _capture_loop(self):
        log("Capture loop started")
        buffer = b''
        frame_count_local = 0
        stdout = self.rpicam_process.stdout
        while self.active and self.rpicam_process and self.rpicam_process.poll() is None:
            try:
                chunk = stdout.read(4096)
                if not chunk:
                    log("rpicam stdout ended")
                    break
                buffer += chunk

                while True:
                    s = buffer.find(b'\xff\xd8')
                    if s < 0: break
                    e = buffer.find(b'\xff\xd9', s)
                    if e < 0: break
                    jpeg = buffer[s:e+2]
                    buffer = buffer[e+2:]

                    # 디코드
                    arr = np.frombuffer(jpeg, np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if frame is None:
                        continue

                    frame_count_local += 1
                    # 큐가 찼으면 가장 오래된 하나 버림
                    if self.frame_queue.full():
                        try: self.frame_queue.get_nowait()
                        except: pass
                    self.frame_queue.put(frame)

                    if frame_count_local % 120 == 0:
                        log(f"Captured {frame_count_local} frames (queue={self.frame_queue.qsize()})")

            except Exception as e:
                log(f"Capture error: {e}")
                time.sleep(0.05)
        log("Capture loop ended")

    # ----- 전송 루프 -----
    def _send_loop(self):
        log("Send loop started")
        base_send_interval = 1.0 / self.target_send_fps
        self._last_send_monotonic = 0
        while self.active:
            try:
                now_m = time.monotonic()
                in_burst = now_m < self._burst_end_time
                interval = (1.0 / WARMUP_BURST_FPS) if in_burst else base_send_interval

                # 저대역폭 모드에서는 전송 FPS 반감
                if self.low_bw_mode and not in_burst:
                    interval *= 1.8  # 더 낮은 전송 빈도

                if now_m - self._last_send_monotonic < interval:
                    time.sleep(0.002); continue

                # 연속 실패 많으면 preflight 먼저
                if self._net_fail_count >= CONSEC_FAIL_PREFLIGHT:
                    pf_ok = self._preflight_ping()
                    if not pf_ok:
                        self.last_fail_reason = "preflight_ping_failed"
                        self._net_fail_count += 1
                        backoff = min(MAX_BACKOFF, 0.5 * (2 ** min(5, self._net_fail_count)))
                        time.sleep(backoff)
                        continue
                    else:
                        self.last_preflight_ok = True

                if self.frame_queue.empty():
                    time.sleep(0.01); continue

                frame = self.frame_queue.get()
                self._frame_counter += 1

                success = self._send_single_frame(frame, self._frame_counter, in_burst)
                self._last_send_monotonic = now_m

                if not success:
                    # 저대역폭 전환 조건
                    if self._net_fail_count == LOW_BW_TRIGGER:
                        if not self.low_bw_mode:
                            log("⚠️ Entering LOW BANDWIDTH mode (auto)")
                            self.low_bw_mode = True
                    self._net_fail_count += 1
                    # rpicam 재시작 조건
                    if self._net_fail_count == CONSEC_FAIL_RESTART:
                        log("🔄 Restarting rpicam due to consecutive failures")
                        self._restart_rpicam()
                    backoff = min(MAX_BACKOFF, 0.4 * (2 ** min(5, self._net_fail_count)))
                    log(f"Send fail count={self._net_fail_count} backoff={backoff:.2f}s reason={self.last_fail_reason}")
                    time.sleep(backoff)
                else:
                    if self._net_fail_count:
                        log(f"✅ Network recovered (fail_count was {self._net_fail_count})")
                        # 복구 시 일부 조건에서 저대역폭 유지 (프레임 확보됨) -> 원상복귀는 사용자 판단
                    self._net_fail_count = 0
                    self.last_fail_reason = ""

            except Exception as e:
                self.last_fail_reason = f"loop_error:{e}"
                log(f"Send loop error: {e}")
                time.sleep(0.3)
        log("Send loop ended")

    def _preflight_ping(self):
        url = f"{self.server_url}/api/stream/ping"
        try:
            r = self.session.get(url, timeout=2)
            if r.status_code == 200:
                return True
            self.last_fail_reason = f"ping_http_{r.status_code}"
            return False
        except Exception as e:
            self.last_fail_reason = f"ping_exc:{type(e).__name__}"
            return False

    def _restart_rpicam(self):
        try:
            if self.rpicam_process and self.rpicam_process.poll() is None:
                self.rpicam_process.terminate()
                self.rpicam_process.wait(timeout=3)
        except Exception:
            try:
                self.rpicam_process.kill()
            except: pass
        # 저대역폭 모드 강제 유지
        if not self.low_bw_mode:
            self.low_bw_mode = True
        self.start_rpicam_stream()

    def _send_single_frame(self, frame, frame_num, in_burst):
        try:
            quality = 68 if (in_burst or self.low_bw_mode) else 75
            ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not ok:
                self.last_fail_reason = "encode_fail"
                return False

            logical_ts = time.time()
            files = { 'frame': ('frame.jpg', buf.tobytes(), 'image/jpeg') }
            data = {
                'timestamp': logical_ts,
                'device_id': self.device_id,
                'frame_number': frame_num,
                'uuid': short_uuid()
            }
            
            # 통일된 엔드포인트 사용
            resp = self.session.post(f"{self.server_url}/api/detect",
                                     files=files, data=data, timeout=REQUEST_TIMEOUT)
            
            if resp.status_code != 200:
                self.last_fail_reason = f"http_{resp.status_code}"
                return False
                
            try:
                js = resp.json()
                if js.get('success'):
                    det = js.get('detection', {})
                    if det.get('fall_detected'):
                        conf = det.get('confidence', 0)
                        event_id = det.get('recording_event_id')
                        log(f"🚨 낙상 감지됨! (confidence={conf:.2f}, event_id={event_id})")
                return True
            except Exception:
                return True  # JSON 파싱 실패해도 HTTP 200이면 성공으로 간주
                
        except requests.exceptions.Timeout:
            self.last_fail_reason = "timeout"
            return False
        except requests.exceptions.ConnectionError:
            self.last_fail_reason = "conn_error"
            return False
        except Exception as e:
            self.last_fail_reason = f"exc:{type(e).__name__}"
            return False

    # ----- 프로세스/헬스 감시 -----
    def _health_loop(self):
        log("Health loop started")
        while self.active:
            try:
                if self.rpicam_process and self.rpicam_process.poll() is not None:
                    log("rpicam process exited -> restarting")
                    self.start_rpicam_stream()
                time.sleep(5)
            except Exception as e:
                log(f"Health loop error: {e}")
                time.sleep(2)
        log("Health loop ended")

    # ----- 서버 핑 (선택) -----
    def _ping_loop(self):
        log("Ping loop started")
        while self.active:
            try:
                time.sleep(PING_INTERVAL)
                r = self.session.get(f"{self.server_url}/api/stream/ping", timeout=2)
                if r.ok:
                    pj = r.json()
                    age = pj.get('fallback_age_ms')
                    log(f"Ping ok fallback_age_ms={age}")
            except Exception:
                log("Ping fail")
        log("Ping loop ended")

# =========================
# 실행부
# =========================
def parse_args():
    p = argparse.ArgumentParser(description="SafeFall Raspberry Pi Camera Client")
    p.add_argument("--server", default=DEFAULT_SERVER, help="Backend server URL")
    p.add_argument("--device-id", default=DEFAULT_DEVICE, help="Device ID")
    p.add_argument("--fps", type=float, default=DEFAULT_SEND_FPS, help="Send FPS (2~20)")
    p.add_argument("--low-bw", action="store_true", help="Start in low bandwidth mode (reduced resolution/FPS)")
    return p.parse_args()

def main():
    args = parse_args()
    client = RaspberryPiCameraClient(
        server_url=args.server,
        device_id=args.device_id,
        send_fps=args.fps,
        low_bw=args.low_bw
    )

    def _sig_handler(sig, frame):
        log("Signal received -> stopping")
        client.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    if not client.start():
        log("Start failed")
        return

    log("Running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(10)
            # 주기 상태 출력
            qsize = client.frame_queue.qsize()
            log(f"Status: sent_frames={client._frame_counter} queue={qsize} low_bw={client.low_bw_mode} last_fail={client.last_fail_reason or 'none'} fail_count={client._net_fail_count}")
    except KeyboardInterrupt:
        pass
    finally:
        client.stop()
        log("Client terminated")

if __name__ == "__main__":
    main()