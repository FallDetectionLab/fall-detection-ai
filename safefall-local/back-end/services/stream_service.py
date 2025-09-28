"""스트림 전용 서비스"""
from flask import jsonify
import time

def register_stream_routes(app, streaming_handler, get_latest_detection_result):
    """스트림 전용 API 등록"""
    
    @app.route('/api/stream/status')
    def stream_status():
        try:
            status = streaming_handler.get_status()
            return jsonify({
                'stream_active': status.get('streaming_active', False),
                'camera_available': status.get('camera_connected', False),
                'detection_active': status.get('detection_active', False),
                'latest_detection': get_latest_detection_result(),
                'stream_url': '/api/video_feed',
                'fallback_url': '/api/stream/live',
                'success': True
            })
        except Exception as e:
            return jsonify({'error': str(e), 'success': False}), 500

    @app.route('/api/realtime/status')
    def realtime_status():
        try:
            status = streaming_handler.get_status()
            return jsonify({
                'camera_active': status.get('streaming_active', False),
                'detection_active': status.get('detection_active', False),
                'camera_connected': status.get('camera_connected', False),
                'latest_detection': get_latest_detection_result(),
                'server_time': str(time.time()),
                'frame_count': status.get('frame_count', 0),
                'success': True
            })
        except Exception as e:
            return jsonify({'error': str(e), 'success': False}), 500
