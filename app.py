import os, time
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, Blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# -----------------------------
# 0) 기본 설정 / ENV
# -----------------------------
load_dotenv()  # .env 읽기

app = Flask(__name__)

# === CORS 허용 Origin 목록 ===
ALLOWED_ORIGINS = [
    # 개발환경
    "http://localhost:5173",
    "http://localhost:3000",
    # 배포 환경
    "http://safefall2.s3-website.ap-northeast-2.amazonaws.com",
    # 추가 도메인들
    # "https://<cloudfront-domain>",  # CloudFront 사용 시 추가
    # "https://www.yourdomain.com",   # 커스텀 도메인 사용 시 추가
]

# === Flask-CORS 설정(Preflight/Headers/Methods 명시) ===
CORS(
    app,
    resources={r"/*": {"origins": ALLOWED_ORIGINS}},
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Length", "Content-Range"],
    supports_credentials=False,  # 쿠키/세션 사용 시 True + ALLOWED_ORIGINS에 정확한 Origin만
)

AUTH = f"Bearer {os.getenv('AUTH_TOKEN', '')}"

MEDIA_ROOT = os.getenv("MEDIA_ROOT", "./media")
os.makedirs(MEDIA_ROOT, exist_ok=True)

S3_BUCKET = os.getenv("S3_BUCKET", "safefall2")
S3_REGION = os.getenv("AWS_REGION", "ap-northeast-2")

# -----------------------------
# 1) DB 설정
# -----------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///safefall.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(64), nullable=False)
    t_event = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    path = db.Column(db.String(512))  # 저장된 파일 경로 또는 S3 key
    type = db.Column(db.String(16), default="normal")  # normal / frame / fall 등
    is_checked = db.Column(db.Boolean, default=False)  # 확인 상태 추가

# 사용자 테이블 추가
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # 실제로는 해시된 비밀번호
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    
    # 기본 사용자 생성 (더미 데이터와 동일)
    existing_users = User.query.count()
    if existing_users == 0:
        default_users = [
            {"username": "네이버", "password": "12345678!"},
            {"username": "구글", "password": "12345678!"},
            {"username": "카카오", "password": "12345678!"},
            {"username": "dumydata", "password": "12345678!"}
        ]
        for user_data in default_users:
            user = User(username=user_data["username"], password=user_data["password"])
            db.session.add(user)
        db.session.commit()

# -----------------------------
# 2) 유틸
# -----------------------------
def authed(req) -> bool:
    return req.headers.get("Authorization", "") == AUTH

def utc_iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"

def paginate_query(query, page=1, limit=10):
    """페이지네이션 헬퍼 함수"""
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "data": items,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1
        }
    }

# -----------------------------
# 3) 전역 Preflight(OPTIONS) 핸들러 (보강)
# -----------------------------
@app.route("/", methods=["OPTIONS"])
@app.route("/<path:anypath>", methods=["OPTIONS"])
def cors_preflight(anypath=None):
    # Flask-CORS가 헤더를 붙여주므로 204만 반환
    return ("", 204)

# ✅ ADDED: /api/v1 전용 OPTIONS 핸들러(프리픽스 보강)
@app.route("/api/v1", methods=["OPTIONS"])
@app.route("/api/v1/<path:anypath>", methods=["OPTIONS"])
def cors_preflight_api(anypath=None):
    return ("", 204)

# ✅ ADDED: 루트 헬스체크(ALB Health Check와의 호환 보장)
@app.get("/health")
def health_root():
    return {"ok": True}

@app.after_request
def add_cors_headers(resp):
    # 방어적으로 CORS 헤더 보강 (프록시/ALB 경유 시 누락 대비)
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Requested-With"
    resp.headers["Access-Control-Max-Age"] = "600"  # Preflight 캐시(선택)
    return resp

# -----------------------------
# 4) API v1 (Blueprint, /api/v1 prefix)
# -----------------------------
api = Blueprint("api", __name__, url_prefix="/api/v1")

# 4-1) 헬스체크
@api.get("/health")
def health():
    return {"ok": True, "msg": "SafeFall API Server", "version": "1.0.0"}

# 4-2) 인증 API - 로그인
@api.post("/auth/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return {"code": "BAD_REQUEST", "message": "username and password required"}, 400
    
    # 사용자 확인 (실제로는 비밀번호 해시 비교)
    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return {"code": "UNAUTHORIZED", "message": "Invalid credentials"}, 401
    
    # 실제로는 JWT 토큰 생성, 여기서는 단순화
    return {
        "accessToken": f"dummy_token_{user.id}_{int(time.time())}",
        "refreshToken": f"refresh_token_{user.id}",
        "user": {
            "id": user.username,
            "name": user.username
        }
    }, 200

# 4-3) 세션 체크
@api.get("/auth/check-session")
def check_session():
    # 실제로는 JWT 토큰 검증
    auth_header = request.headers.get("Authorization", "")
    if "dummy_token_" in auth_header:
        return {"valid": True, "user": {"id": "current_user"}}, 200
    return {"valid": False}, 401

# 4-4) 영상 목록 API (프론트엔드 기대 형태에 맞춤)
@api.get("/videos")
def get_videos():
    # 쿼리 파라미터 파싱
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    sort_by = request.args.get("sortBy", "t_event")  # 기본값 t_event 권장
    sort_order = request.args.get("sortOrder", "desc")
    search = request.args.get("search", "")
    is_checked = request.args.get("isChecked")
    
    # 쿼리 빌드
    query = Event.query
    
    # 검색 필터
    if search:
        query = query.filter(Event.path.like(f"%{search}%"))
    
    # 확인 상태 필터
    if is_checked is not None:
        is_checked_bool = str(is_checked).lower() == "true"
        query = query.filter(Event.is_checked == is_checked_bool)
    
    # 정렬(필드 검증 보강)
    if hasattr(Event, sort_by):
        column = getattr(Event, sort_by)
    else:
        column = Event.t_event  # 안전 기본값
    query = query.order_by(column.desc() if sort_order == "desc" else column.asc())
    
    # 페이지네이션
    result = paginate_query(query, page, limit)
    
    # 데이터 변환 (프론트엔드 기대 형태로)
    videos = []
    for event in result["data"]:
        filename = event.path.split("/")[-1] if event.path else f"event_{event.id}.mp4"
        videos.append({
            "id": event.id,
            "filename": filename,
            "createdAt": event.t_event.isoformat() if event.t_event else datetime.utcnow().isoformat(),
            "isChecked": event.is_checked,
            "device_id": event.device_id,
            "type": event.type,
            "path": event.path,
            "url": f"/api/v1/media/{event.path}" if event.path else None
        })
    
    return {
        "data": videos,
        "pagination": result["pagination"]
    }, 200

# 4-5) 영상 상세 정보
@api.get("/videos/<video_id>")
def get_video_detail(video_id):
    event = Event.query.get_or_404(video_id)
    filename = event.path.split("/")[-1] if event.path else f"event_{event.id}.mp4"
    
    return {
        "id": event.id,
        "filename": filename,
        "createdAt": event.t_event.isoformat() if event.t_event else datetime.utcnow().isoformat(),
        "isChecked": event.is_checked,
        "device_id": event.device_id,
        "type": event.type,
        "path": event.path,
        "url": f"/api/v1/media/{event.path}" if event.path else None,
        "size": "unknown",  # 실제로는 파일 크기 계산
        "duration": "unknown"  # 실제로는 영상 길이 계산
    }, 200

# 4-6) 영상 확인 상태 업데이트
@api.patch("/videos/<video_id>/status")
def update_video_status(video_id):
    data = request.get_json(force=True, silent=True) or {}
    is_checked = data.get("isChecked")
    
    if is_checked is None:
        return {"code": "BAD_REQUEST", "message": "isChecked field required"}, 400
    
    event = Event.query.get_or_404(video_id)
    event.is_checked = bool(is_checked)
    db.session.commit()
    
    return {
        "success": True,
        "message": "Status updated successfully",
        "isChecked": event.is_checked
    }, 200

# 4-7) 영상 삭제
@api.delete("/videos/<video_id>")
def delete_video(video_id):
    event = Event.query.get_or_404(video_id)
    
    # 실제 파일 삭제 (선택적)
    if event.path and os.path.exists(os.path.join(MEDIA_ROOT, event.path)):
        os.remove(os.path.join(MEDIA_ROOT, event.path))
    
    db.session.delete(event)
    db.session.commit()
    
    return {"success": True, "message": "Video deleted successfully"}, 200

# 4-8) 대시보드 통계
@api.get("/dashboard/stats")
def get_dashboard_stats():
    total_videos = Event.query.count()
    checked_videos = Event.query.filter_by(is_checked=True).count()
    unchecked_videos = total_videos - checked_videos
    
    # 오늘 영상 수
    today = datetime.utcnow().date()
    today_videos = Event.query.filter(
        Event.t_event >= datetime.combine(today, datetime.min.time())
    ).count()
    
    return {
        "totalVideos": total_videos,
        "checkedVideos": checked_videos,
        "uncheckedVideos": unchecked_videos,
        "todayVideos": today_videos,
        "checkRate": round((checked_videos / total_videos * 100) if total_videos > 0 else 0, 1)
    }, 200

# 4-9) 최근 영상 목록
@api.get("/dashboard/recent-videos")
def get_recent_videos():
    limit = int(request.args.get("limit", 6))
    
    recent_events = Event.query.order_by(Event.t_event.desc()).limit(limit).all()
    
    videos = []
    for event in recent_events:
        filename = event.path.split("/")[-1] if event.path else f"event_{event.id}.mp4"
        videos.append({
            "id": event.id,
            "filename": filename,
            "createdAt": event.t_event.isoformat() if event.t_event else datetime.utcnow().isoformat(),
            "isChecked": event.is_checked,
            "device_id": event.device_id,
            "type": event.type
        })
    
    return {"data": videos}, 200

# 4-10) 차트 데이터
@api.get("/dashboard/chart-data")
def get_chart_data():
    period = request.args.get("period", "month")
    
    # 간단한 더미 차트 데이터 (실제로는 복잡한 집계 쿼리)
    if period == "month":
        # 월별 데이터
        chart_data = []
        for month in range(1, 12 + 1):
            start = datetime(2024, month, 1)
            end = datetime(2025, 1, 1) if month == 12 else datetime(2024, month + 1, 1)
            month_events = Event.query.filter(
                Event.t_event >= start,
                Event.t_event < end
            ).count()
            
            checked_count = Event.query.filter(
                Event.t_event >= start,
                Event.t_event < end,
                Event.is_checked == True
            ).count()
            
            chart_data.append({
                "date": f"{month:02d}월",
                "xPosition": month,
                "total": month_events,
                "checked": checked_count,
                "unchecked": month_events - checked_count
            })
        
        return {"data": chart_data}, 200
    
    return {"data": []}, 200

# 4-11) 실시간 스트림 정보
@api.get("/stream/live")
def get_live_stream():
    return {
        "streamUrl": "http://192.168.0.6:5000",  # 라즈베리파이 주소 (배포환경 접근 불가 가능성 주의)
        "type": "http",
        "status": "online",
        "quality": "720p"
    }, 200

# 4-12) 스트림 상태
@api.get("/stream/status")
def get_stream_status():
    return {
        "status": "online",
        "uptime": "24h 15m",
        "viewers": 1
    }, 200

# === 기존 API들 유지 ===
# 4-13) 로컬 미디어 파일 서빙(테스트용)
@api.get("/media/<path:subpath>")
def get_media(subpath):
    """테스트/편의용: 로컬 MEDIA_ROOT 파일 서빙"""
    full = os.path.join(MEDIA_ROOT, subpath)
    d, f = os.path.split(full)
    return send_from_directory(d, f)

# 4-14) 로컬 저장(직접 업로드) — 프레임
@api.post("/ingest/frame")
def ingest_frame():
    if not authed(request):
        return {"code": "UNAUTHORIZED", "message": "invalid token"}, 401

    file = request.files.get("frame")
    device_id = request.form.get("device_id", "unknown")
    if not file:
        return {"code": "BAD_REQUEST", "message": "no frame file"}, 400

    day = datetime.utcnow().strftime("%Y/%m/%d")
    save_dir = os.path.join(MEDIA_ROOT, day, device_id)
    os.makedirs(save_dir, exist_ok=True)

    fname = f"snapshot_{int(time.time())}.jpg"
    rel_key = os.path.join(day, device_id, fname)
    path = os.path.join(MEDIA_ROOT, rel_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file.save(path)

    evt = Event(device_id=device_id, path=rel_key, type="frame")
    db.session.add(evt)
    db.session.commit()

    return {
        "ok": True,
        "event": {
            "id": evt.id,
            "device_id": evt.device_id,
            "t_event": evt.t_event.isoformat(),
            "path": evt.path,
            "url": f"/api/v1/media/{evt.path}",
            "type": evt.type,
        },
        "ts": request.form.get("ts"),
    }, 200

# 4-15) 로컬 저장(직접 업로드) — 클립
@api.post("/ingest/clip")
def ingest_clip():
    if not authed(request):
        return {"code": "UNAUTHORIZED", "message": "invalid token"}, 401

    file = request.files.get("clip")
    device_id = request.form.get("device_id", "unknown")
    if not file:
        return {"code": "BAD_REQUEST", "message": "no clip file"}, 400

    day = datetime.utcnow().strftime("%Y/%m/%d")
    save_dir = os.path.join(MEDIA_ROOT, day, device_id)
    os.makedirs(save_dir, exist_ok=True)

    fname = f"clip_{int(time.time())}.mp4"
    rel_key = os.path.join(day, device_id, fname)
    path = os.path.join(MEDIA_ROOT, rel_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file.save(path)

    evt = Event(device_id=device_id, path=rel_key, type="fall")
    db.session.add(evt)
    db.session.commit()

    return {
        "ok": True,
        "event": {
            "id": evt.id,
            "device_id": evt.device_id,
            "t_event": evt.t_event.isoformat(),
            "path": evt.path,
            "url": f"/api/v1/media/{evt.path}",
            "type": evt.type,
        },
        "ts": request.form.get("ts"),
    }, 200

# === 블루프린트 등록 ===
app.register_blueprint(api)

@app.before_request
def _log_path():
    print(f"[REQ] {request.method} {request.path}")

# 2) 라우트 맵 확인용
@app.get("/__routes")
def __routes():
    return {
        "rules": [str(r) for r in app.url_map.iter_rules()]
    }

# -----------------------------
# 5) 로컬 실행 (개발용)
# -----------------------------
if __name__ == "__main__":
    print(">>> SafeFall Flask 서버 시작")
    print(">>> AUTH in server =", repr(AUTH))
    print(">>> S3_BUCKET =", repr(S3_BUCKET), " / AWS_REGION =", repr(S3_REGION))
    print(">>> CORS Origins =", ALLOWED_ORIGINS)
    # 운영은 gunicorn/uwsgi + Nginx/ALB 권장
    app.run(host="0.0.0.0", port=5000, debug=True)
