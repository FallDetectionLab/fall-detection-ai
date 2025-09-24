import os, time
from datetime import datetime, date
from flask import Blueprint, request, send_from_directory

from sf_models.entities import db, Event
from utils.helpers import utc_iso_now, paginate_query, build_media_url
from services.auth_service import authed

dash_bp = Blueprint("dash", __name__)
MEDIA_ROOT = os.getenv("MEDIA_ROOT", "./media")
os.makedirs(MEDIA_ROOT, exist_ok=True)

@dash_bp.get("/videos")
def get_videos():
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    sort_by = request.args.get("sortBy", "t_event")
    sort_order = request.args.get("sortOrder", "desc")
    search = request.args.get("search", "")
    is_checked = request.args.get("isChecked")
    type_filter = request.args.get("type")

    query = Event.query
    if search:
        query = query.filter(Event.path.like(f"%{search}%"))
    if is_checked is not None:
        is_checked_bool = str(is_checked).lower() == "true"
        query = query.filter(Event.is_checked == is_checked_bool)
    if type_filter:
        query = query.filter(Event.type == type_filter)

    column = getattr(Event, sort_by, Event.t_event)
    query = query.order_by(column.desc() if sort_order == "desc" else column.asc())

    result = paginate_query(query, page, limit)
    videos = []
    for e in result["data"]:
        filename = e.path.split("/")[-1] if e.path else f"event_{e.id}.mp4"
        videos.append({
            "id": e.id,
            "filename": filename,
            "createdAt": e.t_event.isoformat() if e.t_event else utc_iso_now(),
            "isChecked": e.is_checked,
            "device_id": e.device_id,
            "type": e.type,
            "path": e.path,
            "url": build_media_url(e.path),
        })
    return {"data": videos, "pagination": result["pagination"]}, 200

@dash_bp.get("/videos/<video_id>")
def get_video_detail(video_id):
    e = Event.query.get_or_404(video_id)
    filename = e.path.split("/")[-1] if e.path else f"event_{e.id}.mp4"
    return {
        "id": e.id,
        "filename": filename,
        "createdAt": e.t_event.isoformat() if e.t_event else utc_iso_now(),
        "isChecked": e.is_checked,
        "device_id": e.device_id,
        "type": e.type,
        "path": e.path,
        "url": build_media_url(e.path),
        "size": "unknown",
        "duration": "unknown"
    }, 200

@dash_bp.patch("/videos/<video_id>/status")
def update_video_status(video_id):
    data = request.get_json(force=True, silent=True) or {}
    is_checked = data.get("isChecked")
    if is_checked is None:
        return {"code": "BAD_REQUEST", "message": "isChecked field required"}, 400
    e = Event.query.get_or_404(video_id)
    e.is_checked = bool(is_checked)
    db.session.commit()
    return {"success": True, "message": "Status updated successfully", "isChecked": e.is_checked}, 200

@dash_bp.delete("/videos/<video_id>")
def delete_video(video_id):
    e = Event.query.get_or_404(video_id)
    if e.path and os.path.exists(os.path.join(MEDIA_ROOT, e.path)):
        try:
            os.remove(os.path.join(MEDIA_ROOT, e.path))
        except Exception:
            pass
    db.session.delete(e); db.session.commit()
    return {"success": True, "message": "Video deleted successfully"}, 200

@dash_bp.get("/dashboard/stats")
def get_dashboard_stats():
    total = Event.query.count()
    checked = Event.query.filter_by(is_checked=True).count()
    unchecked = total - checked
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_videos = Event.query.filter(Event.t_event >= today_start).count()
    return {
        "totalVideos": total,
        "checkedVideos": checked,
        "uncheckedVideos": unchecked,
        "todayVideos": today_videos,
        "checkRate": round((checked / total * 100) if total > 0 else 0, 1)
    }, 200

@dash_bp.get("/dashboard/recent-videos")
def get_recent_videos():
    limit = int(request.args.get("limit", 6))
    rows = Event.query.order_by(Event.t_event.desc()).limit(limit).all()
    videos = []
    for e in rows:
        filename = e.path.split("/")[-1] if e.path else f"event_{e.id}.mp4"
        videos.append({
            "id": e.id,
            "filename": filename,
            "createdAt": e.t_event.isoformat() if e.t_event else utc_iso_now(),
            "isChecked": e.is_checked,
            "device_id": e.device_id,
            "type": e.type,
            "url": build_media_url(e.path),
        })
    return {"data": videos}, 200

@dash_bp.get("/dashboard/chart-data")
def get_chart_data():
    # 데모용 월별 카운트 (2024년)
    data = []
    for month in range(1, 13):
        start = datetime(2024, month, 1)
        end = datetime(2025, 1, 1) if month == 12 else datetime(2024, month + 1, 1)
        month_events = Event.query.filter(Event.t_event >= start, Event.t_event < end).count()
        checked_count = Event.query.filter(
            Event.t_event >= start, Event.t_event < end, Event.is_checked == True  # noqa
        ).count()
        data.append({
            "date": f"{month:02d}월",
            "xPosition": month,
            "total": month_events,
            "checked": checked_count,
            "unchecked": month_events - checked_count
        })
    return {"data": data}, 200

# 스트림 더미
@dash_bp.get("/stream/live")
def get_live_stream():
    return {"streamUrl": "http://192.168.0.6:5000", "type": "http", "status": "online", "quality": "720p"}, 200

@dash_bp.get("/stream/status")
def get_stream_status():
    return {"status": "online", "uptime": "24h 15m", "viewers": 1}, 200

# 로컬 미디어 서빙
@dash_bp.get("/media/<path:subpath>")
def get_media(subpath):
    full = os.path.join(MEDIA_ROOT, subpath)
    d, f = os.path.split(full)
    resp = send_from_directory(d, f)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

# 로컬 저장 — 프레임
@dash_bp.post("/ingest/frame")
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
    db.session.add(evt); db.session.commit()
    return {
        "ok": True,
        "event": {
            "id": evt.id, "device_id": evt.device_id,
            "t_event": evt.t_event.isoformat(), "path": evt.path,
            "url": build_media_url(evt.path), "type": evt.type,
        },
        "ts": request.form.get("ts"),
    }, 200

# 로컬 저장 — 클립
@dash_bp.post("/ingest/clip")
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
    db.session.add(evt); db.session.commit()
    return {
        "ok": True,
        "event": {
            "id": evt.id, "device_id": evt.device_id,
            "t_event": evt.t_event.isoformat(), "path": evt.path,
            "url": build_media_url(evt.path), "type": evt.type,
        },
        "ts": request.form.get("ts"),
    }, 200
