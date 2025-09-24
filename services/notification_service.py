from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import json
import threading

notification_bp = Blueprint("notifications", __name__)

# 인메모리 알림 저장소
_notifications = []
_notification_id_counter = 1
_lock = threading.Lock()

def authed(req):
    """간단한 인증 체크"""
    auth_header = req.headers.get("Authorization", "")
    return auth_header.startswith("Bearer")

def create_notification(title, message, notification_type="fall_detected", severity="high"):
    """
    새로운 알림을 생성하고 메모리에 저장
    """
    global _notification_id_counter
    
    try:
        with _lock:
            notification = {
                "id": _notification_id_counter,
                "title": title,
                "message": message,
                "type": notification_type,
                "severity": severity,
                "created_at": datetime.now(),
                "is_read": False
            }
            
            _notifications.append(notification)
            _notification_id_counter += 1
            
            # 최대 100개만 유지 (메모리 관리)
            if len(_notifications) > 100:
                _notifications.pop(0)
            
        print(f"✓ 알림 생성됨: {title} (ID: {notification['id']})")
        return True
        
    except Exception as e:
        print(f"✗ 알림 생성 실패: {e}")
        return False

@notification_bp.route("/notifications", methods=["GET"])
def get_notifications():
    """알림 목록 조회"""
    if not authed(request):
        return {"ok": False, "error": "unauthorized"}, 401
    
    try:
        # 쿼리 파라미터
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        unread_only = request.args.get("unread_only", "false").lower() == "true"
        
        with _lock:
            # 필터링
            filtered_notifications = _notifications.copy()
            if unread_only:
                filtered_notifications = [n for n in filtered_notifications if not n["is_read"]]
            
            # 최신순 정렬
            filtered_notifications.sort(key=lambda x: x["created_at"], reverse=True)
            
            # 페이징
            total = len(filtered_notifications)
            paginated = filtered_notifications[offset:offset + limit]
            
            # 응답 포맷 변환
            response_notifications = []
            for notif in paginated:
                response_notifications.append({
                    "id": notif["id"],
                    "title": notif["title"],
                    "message": notif["message"],
                    "type": notif["type"],
                    "severity": notif["severity"],
                    "created_at": notif["created_at"].isoformat(),
                    "is_read": notif["is_read"]
                })
        
        return {
            "ok": True,
            "notifications": response_notifications,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

@notification_bp.route("/notifications/latest", methods=["GET"])
def get_latest_notifications():
    """최신 알림 조회 (프론트엔드 폴링용)"""
    if not authed(request):
        return {"ok": False, "error": "unauthorized"}, 401
    
    try:
        # 최근 5분 이내의 읽지 않은 알림만 조회
        since = datetime.now() - timedelta(minutes=5)
        
        with _lock:
            latest_notifications = []
            for notif in _notifications:
                if notif["created_at"] >= since and not notif["is_read"]:
                    latest_notifications.append({
                        "id": notif["id"],
                        "title": notif["title"],
                        "message": notif["message"],
                        "type": notif["type"],
                        "severity": notif["severity"],
                        "created_at": notif["created_at"].isoformat(),
                        "is_read": notif["is_read"]
                    })
            
            # 최신순 정렬
            latest_notifications.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "ok": True,
            "notifications": latest_notifications,
            "count": len(latest_notifications)
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

@notification_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
def mark_as_read(notification_id):
    """알림을 읽음으로 표시"""
    if not authed(request):
        return {"ok": False, "error": "unauthorized"}, 401
    
    try:
        with _lock:
            for notif in _notifications:
                if notif["id"] == notification_id:
                    notif["is_read"] = True
                    return {"ok": True, "message": "marked as read"}
            
            return {"ok": False, "error": "notification not found"}, 404
                
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

@notification_bp.route("/notifications/mark-all-read", methods=["POST"])
def mark_all_read():
    """모든 알림을 읽음으로 표시"""
    if not authed(request):
        return {"ok": False, "error": "unauthorized"}, 401
    
    try:
        count = 0
        with _lock:
            for notif in _notifications:
                if not notif["is_read"]:
                    notif["is_read"] = True
                    count += 1
        
        return {
            "ok": True, 
            "message": f"{count} notifications marked as read"
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

@notification_bp.route("/notifications/test", methods=["POST"])
def create_test_notification():
    """테스트용 알림 생성 (프론트엔드 테스트용)"""
    if not authed(request):
        return {"ok": False, "error": "unauthorized"}, 401
    
    data = request.get_json() or {}
    title = data.get("title", "테스트 낙상 감지")
    message = data.get("message", "거실에서 낙상이 감지되었습니다.")
    
    success = create_notification(
        title=title,
        message=message,
        notification_type="fall_detected",
        severity="high"
    )
    
    if success:
        return {"ok": True, "message": "test notification created"}
    else:
        return {"ok": False, "error": "failed to create notification"}, 500

@notification_bp.route("/notifications/stats", methods=["GET"])
def get_notification_stats():
    """알림 통계 (대시보드용)"""
    if not authed(request):
        return {"ok": False, "error": "unauthorized"}, 401
    
    try:
        with _lock:
            total = len(_notifications)
            unread = len([n for n in _notifications if not n["is_read"]])
            today = datetime.now().date()
            today_count = len([n for n in _notifications if n["created_at"].date() == today])
            
            # 심각도별 통계
            severity_stats = {"high": 0, "medium": 0, "low": 0}
            for notif in _notifications:
                severity = notif.get("severity", "medium")
                if severity in severity_stats:
                    severity_stats[severity] += 1
        
        return {
            "ok": True,
            "stats": {
                "total": total,
                "unread": unread,
                "today": today_count,
                "by_severity": severity_stats
            }
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500
