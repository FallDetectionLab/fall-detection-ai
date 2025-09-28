"""통합 API 라우트 서비스 (핵심 기능만 유지)"""
from flask import jsonify, request, Response
import time
from .recording_service import recording_manager
from .database_service import unified_db
from .detection_service import detect_fall_in_frame_with_recording
from .streaming_service import StreamState, StreamBuilder
from pathlib import Path

# 전역 스트림 상태
stream_state = StreamState()

# 원격 프레임 카운터
REMOTE_FEED = {'frames': 0, 'last_ts': 0.0}

def register_core_api_routes(app):
    """핵심 API 라우트만 등록"""
    
    @app.after_request
    def after_request(resp):
        resp.headers.add('Access-Control-Allow-Origin','*')
        resp.headers.add('Access-Control-Allow-Headers','Content-Type,Authorization')
        resp.headers.add('Access-Control-Allow-Methods','GET,PUT,POST,DELETE,OPTIONS')
        return resp
    
    # === 스트림 관련 ===
    @app.route('/api/stream/status')
    def stream_status():
        try:
            return jsonify({
                'stream_active': True,  # 라즈베리파이 연결 상태
                'camera_available': True,
                'detection_active': True,
                'remote_frames': REMOTE_FEED['frames'],
                'remote_last_age_ms': (time.time()-REMOTE_FEED['last_ts'])*1000 if REMOTE_FEED['last_ts'] else None,
                'success': True
            })
        except Exception as e:
            return jsonify({'error': str(e), 'success': False}), 500
    
    # === 감지 및 녹화 ===
    @app.route('/api/detect', methods=['POST'])
    def detect_frame():
        """실제 프레임 감지 처리"""
        try:
            if 'frame' not in request.files:
                return jsonify({'error':'No frame provided','success': False}), 400
            
            file = request.files['frame']
            device_id = request.form.get('device_id', 'raspberry_pi_camera')
            timestamp = float(request.form.get('timestamp', time.time()))
            
            # 프레임 디코딩
            file.seek(0)
            data = file.read()
            
            import numpy as np, cv2
            nparr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return jsonify({'error':'Failed to decode frame','success': False}), 400
            
            # 스트림 상태 업데이트
            stream_state.update_jpeg(data)
            REMOTE_FEED['frames'] += 1
            REMOTE_FEED['last_ts'] = time.time()
            
            # 녹화 버퍼에 프레임 추가
            recording_manager.push_frame(timestamp, frame)
            
            # 실제 감지 수행
            detection_result = detect_fall_in_frame_with_recording(frame)
            
            # 낙상 감지 시 녹화 시작
            if detection_result.get('fall_detected', False):
                confidence = detection_result.get('confidence', 0.0)
                recording_id = recording_manager.start_recording(
                    confidence=confidence,
                    device_id=device_id,
                    trigger_reason='ai_detection'
                )
                
                if recording_id:
                    detection_result['recording_event_id'] = recording_id
                    print(f"🚨 Fall detected! Recording started: {recording_id}")
            
            detection_result['remote_frames_total'] = REMOTE_FEED['frames']
            return jsonify({'detection': detection_result, 'success': True})
            
        except Exception as e:
            return jsonify({'error': f"Detection error: {e}", 'success': False}), 500
    
    @app.route('/api/detect/mock', methods=['POST'])
    def mock_fall_detection():
        """Mock 낙상 감지 (브라우저 콘솔 테스트용)"""
        try:
            body = request.get_json(force=True) if request.is_json else {}
            confidence = float(body.get('confidence', 0.9))
            device_id = body.get('device_id', 'mock_device')
            quick = body.get('quick', True)  # 기본적으로 8초 녹화
            
            # Mock 감지 결과 생성
            mock_result = {
                'fall_detected': True,
                'confidence': confidence,
                'raw_flag': True,
                'bbox': [100, 120, 200, 260],
                'timestamp': time.time(),
                'device_id': device_id,
                'mock': True
            }
            
            # 녹화 시작 (8초 단축 버전)
            recording_id = recording_manager.start_recording(
                confidence=confidence,
                device_id=device_id,
                trigger_reason='mock_test'
            )
            
            if recording_id:
                mock_result['recording_event_id'] = recording_id
                print(f"🧪 Mock fall detection triggered! Recording: {recording_id}")
            
            return jsonify({
                'success': True,
                'detection': mock_result,
                'message': 'Mock fall detection triggered',
                'recording_duration': '8 seconds (test mode)',
                'recording_id': recording_id
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # === 대시보드 데이터 ===
    @app.route('/api/dashboard/recent-videos')
    def dashboard_recent_videos():
        """대시보드용 최근 영상 목록 (통합 DB + 녹화 중인 것)"""
        try:
            limit = int(request.args.get('limit', 6))
            
            # DB에서 저장된 이벤트들
            db_events = unified_db.get_recent_events(limit * 2)
            
            # 현재 녹화 중인 이벤트들 (메모리)
            recording_events = recording_manager.get_recent_events(10)
            
            # 통합 및 정렬
            all_events = []
            
            # DB 이벤트 추가
            for event in db_events:
                all_events.append({
                    'id': event['id'],
                    'filename': event['filename'],
                    'createdAt': event['timestamp'],
                    'isChecked': event['processed'],
                    'device_id': event['device_id'],
                    'type': 'fall',
                    'confidence': event['confidence'],
                    'duration_sec': event.get('duration_sec', 0),
                    'url': event['url'],
                    'ready': event['ready'],
                    'recording': False,  # DB 저장된 것은 완료
                    'failed': event['failed']
                })
            
            # 녹화 중인 이벤트 추가
            for event in recording_events:
                if event.get('recording', False):  # 아직 녹화 중인 것만
                    all_events.append({
                        'id': event['id'],
                        'filename': event['filename'],
                        'createdAt': event['timestamp'],
                        'isChecked': False,
                        'device_id': event['device_id'],
                        'type': 'fall',
                        'confidence': event['confidence'],
                        'duration_sec': 0,  # 녹화 중이므로 0
                        'url': None,  # 아직 준비 안됨
                        'ready': False,
                        'recording': True,
                        'failed': False
                    })
            
            # 시간순 정렬 및 제한
            all_events.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
            
            return jsonify({
                'data': all_events[:limit],
                'success': True
            })
            
        except Exception as e:
            return jsonify({'error': str(e), 'success': False}), 500
    
    @app.route('/api/dashboard/stats')  
    def dashboard_stats():
        """대시보드 통계"""
        try:
            stats = unified_db.get_stats()
            return jsonify({
                'totalVideos': stats['total'],
                'checkedVideos': stats['processed'],
                'uncheckedVideos': stats['unprocessed'],
                'todayVideos': stats['today'],
                'checkRate': stats['process_rate'],
                'success': True
            })
        except Exception as e:
            return jsonify({'error': str(e), 'success': False}), 500
    
    # === 영상 관련 ===
    @app.route('/api/events/video/<int:event_id>')
    def get_event_video(event_id):
        """통합 영상 스트리밍"""
        try:
            # DB에서 먼저 조회
            event = unified_db.get_event_by_id(event_id)
            if not event:
                # 메모리(녹화 중)에서 조회
                event = recording_manager.get_event_by_id(event_id)
            
            if not event:
                return jsonify({'error': 'Event not found', 'success': False}), 404
                
            video_path = event.get('video_path')
            if not video_path or not Path(video_path).exists():
                return jsonify({'error': 'Video file not found', 'success': False}), 404
            
            def generate():
                with open(video_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            
            response = Response(generate(), mimetype='video/mp4')
            response.headers['Content-Disposition'] = f'inline; filename="{Path(video_path).name}"'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            return jsonify({'error': str(e), 'success': False}), 500
    
    @app.route('/api/events/<int:event_id>/check', methods=['PATCH'])
    def mark_event_checked(event_id):
        """이벤트 확인 완료 표시"""
        try:
            success = unified_db.mark_processed(event_id)
            return jsonify({'success': success, 'id': event_id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

# 통합 라우트 등록 함수
def register_api_routes(app, streaming_handler, get_fall_events, get_pending_alerts,
                        get_latest_notifications, get_notification_stats,
                        get_latest_detection_result, set_simulation_mode,
                        detect_fall_in_frame_with_recording):
    """기존 호환성을 위한 래퍼"""
    register_core_api_routes(app)
    
    # 스트림 빌더 등록
    stream_builder = StreamBuilder(streaming_handler, stream_state)
    
    @app.route('/api/video_feed')
    def video_feed():
        return stream_builder.build()
    
    @app.route('/api/stream/live')  
    def live_stream():
        return stream_builder.build()

# 브라우저 콘솔 테스트 함수 추가
def add_console_test_functions():
    """프론트엔드에 테스트 함수들 추가"""
    return """
    <script>
    // 브라우저 콘솔에서 사용할 테스트 함수들
    window.testFallDetection = function(confidence = 0.9) {
        fetch('/api/detect/mock', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                confidence: confidence,
                device_id: 'console_test',
                quick: true
            })
        })
        .then(r => r.json())
        .then(data => {
            console.log('🧪 Mock fall detection result:', data);
            if (data.success) {
                alert(`낙상 감지 테스트 성공!\\n녹화 ID: ${data.recording_id}\\n8초 후 영상 확인 가능`);
            }
        })
        .catch(e => console.error('Test failed:', e));
    };
    
    window.checkRecordingStatus = function() {
        fetch('/api/recording/status')
        .then(r => r.json())
        .then(data => console.log('📹 Recording status:', data))
        .catch(e => console.error('Status check failed:', e));
    };
    </script>
    """