import os, time
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_cors import CORS

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # 운영 전에는 도메인 제한

# --- 1) ENV / MEDIA ---
AUTH = f"Bearer {os.getenv('AUTH_TOKEN','')}"
MEDIA_ROOT = os.getenv("MEDIA_ROOT", "./media")
os.makedirs(MEDIA_ROOT, exist_ok=True)

# --- 2) DB 설정+초기화 ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///safefall.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(64), nullable=False)
    t_event = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    path = db.Column(db.String(512))  # 저장된 파일 경로
    type = db.Column(db.String(16), default="normal")  # normal / fall 등


with app.app_context():
    db.create_all()


# --- 3) 공용 함수/라우트 ---
def authed(req):
    return req.headers.get("Authorization", "") == AUTH


@app.get("/health")
def health():
    return {"ok": True, "msg": "hello"}


# 정적 파일 서빙(테스트 편의)
@app.get("/media/<path:subpath>")
def get_media(subpath):
    full = os.path.join(MEDIA_ROOT, subpath)
    d, f = os.path.split(full)
    return send_from_directory(d, f)


# --- 4) 프레임 수신(이미지) ---
@app.post("/ingest/frame")
def ingest_frame():
    if not authed(request):
        return {"code": "UNAUTHORIZED", "message": "invalid token"}, 401

    file = request.files.get("frame")
    device_id = request.form.get("device_id", "unknown")
    ts = request.form.get("ts", str(time.time()))
    if not file:
        return {"code": "BAD_REQUEST", "message": "no frame file"}, 400

    day = datetime.utcnow().strftime("%Y/%m/%d")
    save_dir = os.path.join(MEDIA_ROOT, day, device_id)
    os.makedirs(save_dir, exist_ok=True)

    fname = f"snapshot_{int(time.time())}.jpg"
    rel_key = os.path.join(day, device_id, fname)  # 상대 경로(표시용)
    path = os.path.join(MEDIA_ROOT, rel_key)  # 실제 저장 경로
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
            "path": evt.path,  # /media/<evt.path> 로 접속 가능
            "type": evt.type,
        },
        "ts": ts,
    }, 200


# --- 5) 클립 수신(영상) ---
@app.post("/ingest/clip")
def ingest_clip():
    if not authed(request):
        return {"code": "UNAUTHORIZED", "message": "invalid token"}, 401

    file = request.files.get("clip")
    device_id = request.form.get("device_id", "unknown")
    ts = request.form.get("ts", str(time.time()))
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
            "type": evt.type,
        },
        "ts": ts,
    }, 200


# --- 6) 이벤트 리스트 ---
@app.get("/events")
def list_events():
    rows = Event.query.order_by(Event.t_event.desc()).limit(50).all()
    return {
        "items": [
            {
                "id": r.id,
                "device_id": r.device_id,
                "t_event": r.t_event.isoformat(),
                "path": r.path,
                "type": r.type,
                "url": f"/media/{r.path}" if r.path else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


# --- 7) 실행 ---
if __name__ == "__main__":
    print(">>> Flask 서버 시작")
    print(">>> AUTH in server =", repr(AUTH))
    app.run(host="127.0.0.1", port=5000, debug=True)
