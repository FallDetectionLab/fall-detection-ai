# Gunicorn 설정 파일
import multiprocessing
import os

# 바인드 주소
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"

# 워커 프로세스 수 (CPU 코어 * 2 + 1)
workers = multiprocessing.cpu_count() * 2 + 1

# 워커 클래스
worker_class = "sync"

# 워커 연결 수
worker_connections = 1000

# 최대 요청 수 (워커 재시작 기준)
max_requests = 1000
max_requests_jitter = 50

# 타임아웃 설정
timeout = 30
keepalive = 2

# 로그 설정
loglevel = "info"
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"

# 데몬 모드 (백그라운드 실행)
daemon = False

# PID 파일
pidfile = "/var/run/gunicorn/gunicorn.pid"

# 사용자/그룹 설정 (보안)
user = "www-data"
group = "www-data"

# 프리로드 (메모리 효율성)
preload_app = True

# 워커 재활용 설정
max_requests = 1000
max_requests_jitter = 100

# 임시 디렉토리
tmp_upload_dir = None