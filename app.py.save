# app.py (RTMP 스트림 처리 포함 / Flask 3.x 호환)
import os, sys, threading
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sf_models.entities import db, seed_dummy_users, ensure_tables
from services.auth_service import auth_bp
from services.s3_service import s3_bp
from services.dashboard import dash_bp
from detection.detect_routes import detect_bp
from services.notification_service import notification_bp

# RTMP 스트림 처리 모듈 import
try:
    from rtmp_stream_processor import create_rtmp_routes, start_rtmp_processing
    RTMP_AVAILABLE = True
    print("✅ RTMP 스트림 처리 모듈 로딩됨")
except ImportError as e:
    print(f"⚠️  RTMP 모듈 로딩 실패: {e}")
    RTMP_AVAILABLE = False

# RTMP lazy-start 플래그/락
_rtmp_started = False
_rtmp_lock = threading.Lock()

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URL", "sqlite:///safefall.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.url_map.strict_slashes = False

# CORS 설정
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://safefall2.s3-website.ap-northeast-2.amazonaws.com",
]
CORS(
    app,
    resources={r"/*": {"origins": ALLOWED_ORIGINS}},
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Length", "Content-Range"],
    supports_credentials=False,
)

# DB 초기화
db.init_app(app)
with app.app_context():
    ensure_tables()
    seed_dummy_users()

# 블루프린트 등록
app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
app.register_blueprint(s3_bp, url_prefix="/api/v1")
app.register_blueprint(dash_bp, url_prefix="/api/v1")
app.register_blueprint(detect_bp, url_prefix="/api/v1")
app.register_blueprint(notification_bp, url_prefix="/api/v1")

# RTMP 라우트 등록
if RTMP_AVAILABLE:
    try:
        create_rtmp_routes(app)
        print("✅ RTMP 라우트 등록 완료")
    except Exception as e:
        print(f"⚠️ RTMP 라우트 등록 실패: {e}")
        RTMP_AVAILABLE = False

@app.get("/health")
def health_root():
    rtmp_status = "enabled" if RTMP_AVAILABLE else "disabled"
    return {
        "ok": True,
        "msg": "SafeFall API Server",
        "version": "1.0.0",
        "rtmp_processing": rtmp_status,
    }

@app.get("/__envcheck")
def envcheck():
    return {
        "YOLO_WEIGHTS": os.getenv("YOLO_WEIGHTS"),
        "YOLOV5_REPO": os.getenv("YOLOV5_REPO"),
        "S3_BUCKET": os.getenv("S3_BUCKET"),
        "AWS_REGION": os.getenv("AWS_REGION"),
        "RTMP_ENABLED": RTMP_AVAILABLE,
    }

@app.get("/__pathcheck")
def __pathcheck():
    yolo_repo = os.getenv("YOLOV5_REPO", "/srv/flaskapp/yolov5")
    return {
        "cwd": os.getcwd(),
        "sys_path_head": sys.path[:8],
        "yolo_repo_path": yolo_repo,
        "yolov5_exists": os.path.exists(yolo_repo),
        "yolov5_is_dir": os.path.isdir(yolo_repo),
        "rtmp_available": RTMP_AVAILABLE,
    }

@app.get("/__importcheck")
def __importcheck():
    import traceback, importlib, torch

    yolo_repo = os.getenv("YOLOV5_REPO", "/srv/flaskapp/yolov5")

    out = {
        "sys_path": sys.path[:5],
        "cwd": os.getcwd(),
        "yolo_repo_path": yolo_repo,
        "yolo_repo_exists": os.path.exists(yolo_repo),
        "rtmp_available": RTMP_AVAILABLE,
    }

    # YOLOv5 기본 모듈 테스트
    try:
        if yolo_repo not in sys.path:
            sys.path.insert(0, yolo_repo)
        from models.common import DetectMultiBackend
        out["yolo_detectmultibackend"] = "✓ OK"
    except Exception as e:
        out["yolo_detectmultibackend_err"] = str(e)
        out["yolo_detectmultibackend_traceback"] = traceback.format_exc()

    try:
        from utils.torch_utils import select_device
        _ = select_device("cpu")
        out["yolo_torch_utils"] = "✓ OK"
    except Exception as e:
        out["yolo_torch_utils_err"] = str(e)

    # PyTorch
    try:
        out["torch_version"] = torch.__version__
        out["cuda_available"] = torch.cuda.is_available()
    except Exception as e:
        out["torch_err"] = str(e)

    # utils.app_utils 테스트 및 모델 로드
    try:
        from utils.app_utils import load_yolo_auto
        out["utils_app_utils"] = "✓ OK"
        flavor, model, names, error = load_yolo_auto()
        out["model_test"] = {
            "flavor": flavor,
            "model_type": str(type(model)),
            "names": names,
            "error": error,
        }
    except Exception as e:
        out["utils_app_utils_err"] = str(e)

    try:
        uh = importlib.import_module("utils.helpers")
        out["utils.helpers"] = getattr(uh, "__file__", "ok")
    except Exception as e:
        out["utils.helpers_err"] = str(e)

    try:
        my = importlib.import_module("models.yolo")
        out["models.yolo"] = getattr(my, "__file__", "ok")
    except Exception as e:
        out["models.yolo_err"] = str(e)

    # OpenCV
    try:
        import cv2
        out["opencv"] = f"✓ OK (version: {cv2.__version__})"
    except Exception as e:
        out["opencv_err"] = str(e)

    return out

@app.get("/__routes")
def __routes():
    return {"rules": [str(r) for r in app.url_map.iter_rules()]}

# Flask 3.x: before_first_request 제거 → 첫 요청 시 한 번만 RTMP 시작
@app.before_request
def _lazy_start_rtmp():
    global _rtmp_started
    if not RTMP_AVAILABLE or _rtmp_started:
        return
    with _rtmp_lock:
        if _rtmp_started:
            return
        try:
            app.logger.info("🚀 RTMP 스트림 처리 자동 시작...")
            start_rtmp_processing()
            _rtmp_started = True
            app.logger.info("✅ RTMP 스트림 처리 시작 완료")
        except Exception as e:
            # 실패해도 서버 전체가 죽지 않도록 예외는 잡고 로그만 남김
            app.logger.exception(f"⚠️  RTMP 자동 시작 실패: {e}")

if __name__ == "__main__":
    print(">>> AUTH =", os.getenv("AUTH_TOKEN", ""))
    print(">>> DB   =", app.config["SQLALCHEMY_DATABASE_URI"])
    print(">>> RTMP =", "ENABLED" if RTMP_AVAILABLE else "DISABLED")
    app.run(host="0.0.0.0", port=8000, debug=True)
