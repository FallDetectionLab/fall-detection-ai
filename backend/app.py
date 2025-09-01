import os, time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

load_dotenv()
app = Flask(__name__)

# --- 1) ENV / MEDIA ---
AUTH = f"Bearer {os.getenv('AUTH_TOKEN','')}"
MEDIA_ROOT = os.getenv("MEDIA_ROOT", "./media")
os.makedirs(MEDIA_ROOT, exist_ok=True)

# --- 2) DB 설정+초기화 (app.run보다 위!) ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///safefall.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(64), nullable=False)
    t_event = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    path = db.Column(db.String(512))
    type = db.Column(db.String(16), default="normal")


with app.app_context():
    db.create_all()


# --- 3) 라우트들 ---
@app.get("/health")
def health():
    return {"ok": True, "msg": "hello"}


def authed(req):
    return req.headers.get("Authorization", "") == AUTH


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
    path = os.path.join(save_dir, fname)
    file.save(path)

    evt = Event(device_id=device_id, path=path)
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


# --- 4) 실행 (맨 마지막) ---
if __name__ == "__main__":
    print(">>> Flask 서버 시작")
    print(">>> AUTH in server =", repr(AUTH))
    app.run(host="127.0.0.1", port=5000, debug=True)
