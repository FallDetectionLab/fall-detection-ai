"""대시보드 전용 서비스"""
from flask import jsonify, request
from datetime import datetime, date

def register_dashboard_routes(app, get_fall_events):
    """대시보드 전용 API 등록"""
    
    @app.route('/api/dashboard/stats')
    def get_dashboard_stats():
        try:
            events = get_fall_events(1000)
            total = len(events)
            
            today = date.today()
            today_events = [e for e in events if e['timestamp'] and 
                           datetime.fromisoformat(e['timestamp']).date() == today]
            
            return jsonify({
                'totalVideos': total,
                'checkedVideos': len([e for e in events if e.get('processed', False)]),
                'uncheckedVideos': len([e for e in events if not e.get('processed', False)]),
                'todayVideos': len(today_events),
                'checkRate': round((len([e for e in events if e.get('processed', False)]) / total * 100) if total > 0 else 0, 1),
                'success': True
            })
        except Exception as e:
            return jsonify({'error': str(e), 'success': False}), 500

    @app.route('/api/dashboard/recent-videos')
    def get_recent_videos():
        try:
            limit = int(request.args.get('limit', 6))
            events = get_fall_events(limit)
            
            videos = []
            for e in events:
                filename = f"fall_event_{e['id']}.mp4" if e.get('video_path') else f"event_{e['id']}.mp4"
                videos.append({
                    'id': e['id'],
                    'filename': filename,
                    'createdAt': e['timestamp'],
                    'isChecked': e.get('processed', False),
                    'device_id': 'raspberry_pi_camera',
                    'type': 'fall',
                    'url': f"/api/events/video/{e['id']}" if e.get('video_path') else None,
                    'confidence': e.get('confidence', 0)
                })
            
            return jsonify({'data': videos, 'success': True})
        except Exception as e:
            return jsonify({'error': str(e), 'success': False}), 500
