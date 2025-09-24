from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(64), nullable=False, default="unknown")
    t_event = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    path = db.Column(db.String(512))
    type = db.Column(db.String(16), default="normal")  # normal/frame/fall
    is_checked = db.Column(db.Boolean, default=False)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # (실서비스: 해시)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def ensure_tables():
    db.create_all()

def seed_dummy_users():
    if User.query.count() == 0:
        for u, p in [("네이버","12345678!"),("구글","12345678!"),("카카오","12345678!"),("dumydata","12345678!")]:
            db.session.add(User(username=u, password=p))
        db.session.commit()
