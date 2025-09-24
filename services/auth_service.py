import time, os
from flask import Blueprint, request
from sf_models.entities import User

auth_bp = Blueprint("auth", __name__)
AUTH = f"Bearer {os.getenv('AUTH_TOKEN', '')}"

def authed(req):
    return req.headers.get("Authorization", "") == AUTH

@auth_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return {"code": "BAD_REQUEST", "message": "username and password required"}, 400
    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return {"code": "UNAUTHORIZED", "message": "Invalid credentials"}, 401
    return {
        "accessToken": f"dummy_token_{user.id}_{int(time.time())}",
        "refreshToken": f"refresh_token_{user.id}",
        "user": {"id": user.username, "name": user.username}
    }, 200

@auth_bp.get("/check-session")
def check_session():
    auth_header = request.headers.get("Authorization", "")
    if "dummy_token_" in auth_header:
        return {"valid": True, "user": {"id": "current_user"}}, 200
    return {"valid": False}, 401
