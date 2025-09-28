import os
from flask import Blueprint, jsonify, request, send_from_directory

def register_video_routes(app, video_service):
    bp = Blueprint("video_routes", __name__, url_prefix="/api/videos")

    @bp.get("/saved")
    def get_saved_videos():
        """디스크에 저장된 비디오 파일들"""
        items = video_service.list_saved_videos()
        return jsonify({"count": len(items), "videos": items, "success": True})
    
    @bp.get("/recent")
    def get_recent_videos():
        """최근 낙상 감지 비디오 (데이터베이스 기반)"""
        try:
            limit = request.args.get('limit', 10, type=int)
            
            # DB에서 최근 낙상 이벤트 가져오기
            from services.database_service import get_fall_events
            events = get_fall_events(limit)
            
            videos = []
            for event in events:
                filename = event.get('video_filename')
                if filename:  # 비디오 파일이 있는 경우만
                    videos.append({
                        'id': event.get('id'),
                        'name': filename,
                        'filename': filename,
                        'title': event.get('title', f'낙상 감지 #{event.get("id")}'),
                        'path': f'/media/videos/{filename}',
                        'url': f'/media/videos/{filename}',
                        'timestamp': event.get('timestamp'),
                        'created_at': event.get('created_at'),
                        'confidence': event.get('confidence', 0.0),
                        'device_id': event.get('device_id', 'unknown'),
                        'processed': event.get('processed', False),
                        'description': event.get('description', '')
                    })
                    
            return jsonify({
                "success": True, 
                "videos": videos, 
                "count": len(videos)
            })
            
        except Exception as e:
            print(f"❌ 최근 비디오 조회 오류: {e}")
            return jsonify({
                "success": False, 
                "videos": [], 
                "count": 0,
                "error": str(e)
            }), 500

    @bp.post("/record")
    def manual_record():
        body = request.get_json(silent=True) or {}
        seconds = int(body.get("seconds", 0)) or None
        filename = body.get("filename")
        res = video_service.start_recording(seconds=seconds, filename=filename)
        return jsonify({"success": bool(res.get("ok")), **res})

    # (선택) 정적 서빙: /media/videos/<filename>
    @app.route("/media/videos/<path:filename>")
    def serve_saved_video(filename):
        # 안전하게 저장 디렉토리에서만 서빙
        dir_path = getattr(video_service, "save_dir", "saved_videos")
        return send_from_directory(directory=dir_path, path=filename, as_attachment=False)

    app.register_blueprint(bp)
