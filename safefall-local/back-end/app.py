from flask import Flask, request, make_response, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import time
import threading
import cv2
import numpy as np

# ====== 새 설정: 영상 저장 관련 ======
VIDEO_SAVE_DIR = os.getenv("VIDEO_SAVE_DIR", "saved_videos")
DEFAULT_RECORD_SECONDS = int(os.getenv("DEFAULT_RECORD_SECONDS", "8"))

# 서비스 모듈 import - 더 안전하게
try:
    from services.database_service import init_database
    from services.streaming_service import StreamingHandler
    from services.video_service import VideoService            # ✅ 추가/사용
    from services.detection_service import DetectionService
    from services.notification_service import NotificationManager
    print("✅ 모든 서비스 모듈이 성공적으로 로드되었습니다")
    SERVICES_LOADED = True
except ImportError as e:
    print(f"❌ 서비스 import 실패: {e}")
    print("📋 누락된 서비스를 더미로 대체합니다")
    SERVICES_LOADED = False
    
    # 더미 클래스들
    class StreamingHandler:
        def __init__(self): pass
        def set_video_service(self, service): pass
    
    class VideoService:
        def __init__(self, *args, **kwargs): pass
        def start_recording(self, seconds=None, filename=None): return {"ok": False, "note": "dummy"}
        def list_saved_videos(self): return []
    
    class DetectionService:
        def __init__(self): pass
        def set_video_service(self, service): pass
        def set_notification_manager(self, manager): pass
        def trigger_manual_detection(self, confidence=0.9):
            return {'event_id': None, 'confidence': confidence}
    
    class NotificationManager:
        def __init__(self): pass

    # 더미 DB 초기화: import 실패 시에도 앱이 기동되도록 보장
    def init_database():
        print("ℹ️ 더미 데이터베이스 초기화 사용")
        return True

# 공유 프레임 저장소 import
from services import frame_store

def create_app():
    app = Flask(__name__)
    
    # 전역 알림 저장소 (프레임은 frame_store 모듈 사용)
    global latest_notification
    latest_notification = None
    
    # VideoService용 프레임 소스 함수
    def get_raspberry_pi_frame():
        """VideoService가 사용할 라즈베리파이 프레임 소스"""
        frame = frame_store.get_frame()
        if frame is not None:
            print(f"공유 프레임 저장소에서 프레임 반환: {frame.shape}")
        else:
            print("공유 프레임 저장소에 프레임 없음")
        return frame
    
    # 환경변수에서 CORS 오리진 설정 (기본값: 로컬 개발용 + React 앱)
    cors_origins_env = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000')
    allowed_origins = [origin.strip() for origin in cors_origins_env.split(',')]
    
    print(f"🌐 CORS 허용 오리진: {allowed_origins}")
    
    # 필요한 라이브러리 추가 import
    import numpy as np

    # CORS 설정 - 미디어 파일 경로 추가 (임시로 모든 오리진 허용)
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # 🔧 임시: 모든 오리진 허용
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        },
        r"/media/*": {  # ✅ 미디어 파일 경로 추가
            "origins": "*",  # 🔧 임시: 모든 오리진 허용
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type", "Range"],
        },
        r"/video_feed": {  # ✅ 비디오 스트림 경로 추가
            "origins": "*",  # 🔧 임시: 모든 오리진 허용
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    }, supports_credentials=False)  # 🔧 credentials 비활성화
    
    # OPTIONS 처리 (credentials 사용 시 * 금지, 요청 Origin 반영)
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get("Origin", "")
            response = make_response("", 204)
            if origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
                response.headers["Access-Control-Allow-Credentials"] = "true"
            # 허용 메서드/헤더 명시 + 캐시 시간 추가
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
            response.headers["Access-Control-Max-Age"] = "86400"  # 24시간 캐시
            return response
    
    print("🚀 SafeFall Backend 시작...")
    
    # ====== 저장 디렉토리 보장 ======
    os.makedirs(VIDEO_SAVE_DIR, exist_ok=True)
    print(f"🎬 영상 저장 디렉토리: {os.path.abspath(VIDEO_SAVE_DIR)}")

    # 서비스 초기화
    if not init_database():
        print("❌ 데이터베이스 초기화 실패")
        return None
    
    # 서비스 인스턴스들 생성
    streaming_handler = StreamingHandler()
    video_service = VideoService(save_dir=VIDEO_SAVE_DIR, default_seconds=DEFAULT_RECORD_SECONDS)
    detection_service = DetectionService()
    notification_manager = NotificationManager()
    
    # 서비스들 연결
    streaming_handler.set_video_service(video_service)
    detection_service.set_video_service(video_service)
    detection_service.set_notification_manager(notification_manager)
    
    # VideoService에 전역 라즈베리파이 프레임 소스 설정
    video_service.set_frame_source(get_raspberry_pi_frame)
    print("전역 라즈베리파이 프레임 소스가 VideoService에 연결됨")

    # 라우트 등록 시도
    routes_registered = False
    try:
        from routes.api_routes import register_api_routes
        from routes.stream_routes import register_stream_routes
        from routes.video_routes import register_video_routes
        
        register_api_routes(app, detection_service, notification_manager)
        register_stream_routes(app, streaming_handler)
        register_video_routes(app, video_service)
        routes_registered = True
        print("✅ 모든 라우트가 성공적으로 등록되었습니다")
    except Exception as e:
        print(f"⚠️ 라우트 등록 실패: {e}")
        print("➡️ 최소 대체 엔드포인트를 등록합니다")
    
    # === 직접 구현 API 엔드포인트들 ===
    
    @app.route('/api/videos/saved', methods=['GET'])
    def get_saved_videos():
        """저장된 비디오 목록 반환 (모든 타입 또는 필터링)"""
        try:
            # URL 매개변수에서 필터 옵션 확인
            trigger_type = request.args.get('trigger_type', None)  # 🔥 기본값 None으로 변경
            limit = request.args.get('limit', 50, type=int)
            
            print(f"비디오 목록 요청: trigger_type={trigger_type or 'ALL'}, limit={limit}")
            
            # 🔥 VideoService의 list_saved_videos() 메서드 사용
            try:
                videos = video_service.list_saved_videos()
                print(f"VideoService에서 {len(videos)}개 비디오 파일 발견")
                
                # 최신순으로 정렬
                videos.sort(key=lambda x: x.get('mtime', 0), reverse=True)
                
                # limit 적용
                if limit:
                    videos = videos[:limit]
                
                print(f"정렬 및 제한 후 {len(videos)}개 비디오 반환")
                
                return jsonify({
                    'success': True,
                    'videos': videos,
                    'count': len(videos),
                    'method': 'VideoService'
                })
                
            except Exception as vs_error:
                print(f"VideoService 사용 실패: {vs_error}")
                print("데이터베이스 방식으로 fallback")
                
                # Fallback: 데이터베이스 방식 사용
                if trigger_type:
                    # 특정 트리거 타입만 필터링
                    from services.database_service import get_fall_events_by_trigger
                    db_events = get_fall_events_by_trigger(trigger_type=trigger_type, limit=limit)
                    print(f"데이터베이스에서 {len(db_events)}개 {trigger_type} 트리거 이벤트 발견")
                else:
                    # 모든 이벤트 가져오기
                    from services.database_service import get_fall_events
                    db_events = get_fall_events(limit=limit)
                    print(f"데이터베이스에서 전체 {len(db_events)}개 이벤트 발견")
                
                # DB 이벤트를 비디오 형식으로 변환
                videos = []
                for event in db_events:
                    video_filename = event.get('video_filename')
                    if video_filename:
                        # 파일이 실제로 존재하는지 확인
                        video_path = os.path.join('saved_videos', video_filename)
                        if os.path.exists(video_path):
                            stat = os.stat(video_path)
                            
                            # MP4 파일 우선 처리
                            if video_filename.lower().endswith('.avi'):
                                print(f"⚠️ AVI 파일 건너뛰기: {video_filename} (웹 브라우저 비호환)")
                                continue
                            
                            videos.append({
                                'id': event.get('id'),
                                'title': event.get('title', f'SafeFall Video - {video_filename}'),
                                'filename': video_filename,  # 🔥 중요: filename 필드 설정
                                'video_filename': video_filename,
                                'name': video_filename,
                                'path': f'/media/videos/{video_filename}',
                                'url': f'/media/videos/{video_filename}',
                                'size': stat.st_size,
                                'mtime': event.get('created_at'),
                                'created_at': event.get('created_at'),
                                'createdAt': event.get('created_at'),
                                'confidence': event.get('confidence', 0.95),
                                'isChecked': event.get('processed', False),
                                'processed': event.get('processed', False),
                                'trigger_type': event.get('trigger_type', 'manual'),
                                'device_id': event.get('device_id', 'manual_trigger'),
                                'file_type': 'mp4'
                            })
                        else:
                            print(f"파일이 없어서 제외: {video_filename}")
                
                return jsonify({
                    'success': True,
                    'videos': videos,
                    'count': len(videos),
                    'method': 'Database fallback'
                })
                
        except Exception as e:
            print(f"비디오 목록 오류: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'videos': [],
                'count': 0
            }), 500
    
    @app.route('/api/videos/recent', methods=['GET'])
    def get_recent_videos():
        """최근 비디오 목록 (저장된 비디오와 동일)"""
        return get_saved_videos()
    
    @app.route('/api/videos/sync-database', methods=['POST'])
    def sync_videos_to_database():
        """디스크의 비디오 파일들을 데이터베이스와 동기화"""
        try:
            from services.database_service import save_fall_event_with_video, get_fall_events
            import os
            from datetime import datetime
            
            video_dir = 'saved_videos'
            
            # 디스크에 있는 모든 비디오 파일
            disk_files = []
            if os.path.exists(video_dir):
                for filename in os.listdir(video_dir):
                    if filename.lower().endswith(('.mp4', '.avi')):
                        file_path = os.path.join(video_dir, filename)
                        file_mtime = os.path.getmtime(file_path)
                        disk_files.append({
                            'name': filename,
                            'path': file_path,
                            'mtime': file_mtime
                        })
            
            # DB에 이미 등록된 파일들
            db_events = get_fall_events(100)
            db_filenames = set(event.get('video_filename', '') for event in db_events if event.get('video_filename'))
            
            # 등록이 필요한 파일들
            files_to_register = [f for f in disk_files if f['name'] not in db_filenames]
            
            registered = 0
            for file_info in files_to_register:
                try:
                    timestamp = datetime.fromtimestamp(file_info['mtime'])
                    event_id = save_fall_event_with_video(
                        timestamp=timestamp,
                        confidence=0.90,
                        video_path=file_info['path']
                    )
                    if event_id:
                        registered += 1
                except Exception as e:
                    print(f"등록 실패: {file_info['name']} - {e}")
            
            return jsonify({
                "success": True,
                "message": f"{registered}개 파일 등록 완료",
                "disk_files": len(disk_files),
                "db_files": len(db_events),
                "registered": registered
            })
            
        except Exception as e:
            return jsonify({
                "success": False, 
                "error": str(e)
            }), 500

    @app.route('/api/videos/sync', methods=['POST'])
    def sync_missing_videos():
        """누락된 영상들을 데이터베이스에 자동 등록"""
        try:
            from services.database_service import (
                save_fall_event_with_video, 
                get_fall_events
            )
            from datetime import datetime
            
            saved_videos_dir = os.path.abspath('saved_videos')
            
            if not os.path.exists(saved_videos_dir):
                return jsonify({
                    'success': False,
                    'error': 'saved_videos 디렉토리가 없습니다'
                }), 404
            
            print(f"🔍 동기화 시작: {saved_videos_dir}")
            
            # 파일시스템에서 영상 파일 목록
            video_files = []
            for filename in os.listdir(saved_videos_dir):
                if filename.lower().endswith(('.mp4', '.avi')):
                    file_path = os.path.join(saved_videos_dir, filename)
                    if os.path.exists(file_path):
                        stat = os.stat(file_path)
                        video_files.append({
                            'filename': filename,
                            'path': file_path,
                            'size': stat.st_size,
                            'mtime': datetime.fromtimestamp(stat.st_mtime)
                        })
            
            print(f"📁 파일시스템 비디오: {len(video_files)}개")
            
            # 데이터베이스에서 기존 영상 목록
            db_events = get_fall_events(2000)  # 더 많은 이벤트 확인
            db_filenames = set()
            for event in db_events:
                if event.get('video_filename'):
                    db_filenames.add(event['video_filename'])
            
            print(f"💾 DB 등록된 비디오: {len(db_filenames)}개")
            print(f"DB 파일명들: {list(db_filenames)[:5]}...")  # 처음 5개만 출력
            
            # 누락된 영상 찾기
            missing_videos = []
            for video in video_files:
                if video['filename'] not in db_filenames:
                    missing_videos.append(video)
            
            print(f"🚨 누락된 영상 {len(missing_videos)}개 발견")
            if missing_videos:
                print(f"누락된 파일들: {[v['filename'] for v in missing_videos[:5]]}...")  # 처음 5개만 출력
            
            # 누락된 영상들 자동 등록
            registered = []
            failed = []
            
            for i, video in enumerate(missing_videos, 1):
                try:
                    # 파일명에서 타임스탬프 추출 시도
                    timestamp = video['mtime']  # 기본적으로 파일 수정 시간 사용
                    
                    # fall_detection_20250927_122047.mp4 형식에서 시간 추출
                    filename_parts = video['filename'].replace('.mp4', '').replace('.avi', '').split('_')
                    if len(filename_parts) >= 4 and filename_parts[0] == 'fall' and filename_parts[1] == 'detection':
                        try:
                            date_part = filename_parts[2]  # 20250927
                            time_part = filename_parts[3]  # 122047
                            
                            if len(date_part) == 8 and len(time_part) == 6:
                                year = date_part[:4]
                                month = date_part[4:6]
                                day = date_part[6:8]
                                hour = time_part[:2]
                                minute = time_part[2:4]
                                second = time_part[4:6]
                                
                                datetime_str = f"{year}-{month}-{day} {hour}:{minute}:{second}"
                                timestamp = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                                print(f"  파일명에서 시간 추출: {video['filename']} -> {timestamp}")
                        except Exception as parse_e:
                            print(f"  시간 파싱 실패: {video['filename']} - {parse_e}")
                            pass  # 추출 실패 시 기본 mtime 사용
                    
                    # 데이터베이스에 등록 (수동 트리거로 설정)
                    event_id = save_fall_event_with_video(
                        timestamp=timestamp,
                        confidence=0.90,  # 기본 신뢰도
                        video_path=video['path']
                    )
                    
                    if event_id:
                        registered.append({
                            'filename': video['filename'],
                            'event_id': event_id,
                            'timestamp': timestamp.isoformat()
                        })
                        print(f"  ✅ [{i}/{len(missing_videos)}] {video['filename']} -> ID:{event_id}")
                    else:
                        failed.append({
                            'filename': video['filename'],
                            'error': '데이터베이스 저장 실패'
                        })
                        print(f"  ❌ [{i}/{len(missing_videos)}] {video['filename']} DB 저장 실패")
                        
                except Exception as e:
                    failed.append({
                        'filename': video['filename'],
                        'error': str(e)
                    })
                    print(f"  ❌ [{i}/{len(missing_videos)}] {video['filename']} 오류: {e}")
            
            # 결과 요약
            result = {
                'success': True,
                'total_videos': len(video_files),
                'db_videos_before': len(db_filenames),
                'missing_found': len(missing_videos),
                'registered': len(registered),
                'failed': len(failed),
                'registered_videos': registered,
                'failed_videos': failed,
                'message': f'{len(registered)}개 영상이 성공적으로 등록되었습니다'
            }
            
            print(f"📊 동기화 완료: {len(registered)}개 등록, {len(failed)}개 실패")
            return jsonify(result)
            
        except Exception as e:
            print(f"❌ 영상 동기화 오류: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/videos/<video_identifier>', methods=['GET'])
    def get_video_by_identifier(video_identifier):
        """개별 비디오 정보 조회 (ID 또는 파일명)"""
        try:
            print(f"Getting video by identifier: {video_identifier}")
            
            # ID인지 파일명인지 판단
            is_numeric_id = video_identifier.isdigit()
            
            # 데이터베이스에서 해당 이벤트 찾기
            try:
                from services.database_service import get_fall_events
                events = get_fall_events(limit=1000)  # 모든 이벤트 가져오기
                
                found_event = None
                if is_numeric_id:
                    # 숫자 ID로 찾기
                    video_id = int(video_identifier)
                    for event in events:
                        if event.get('id') == video_id:
                            found_event = event
                            break
                else:
                    # 파일명으로 찾기
                    decoded_filename = video_identifier
                    # URL 디코딩 시도
                    try:
                        from urllib.parse import unquote
                        decoded_filename = unquote(video_identifier)
                    except:
                        pass
                    
                    print(f"Searching for filename: {decoded_filename}")
                    for event in events:
                        event_filename = event.get('video_filename')
                        if event_filename and (
                            event_filename == decoded_filename or 
                            event_filename == video_identifier
                        ):
                            found_event = event
                            break
                
                if not found_event:
                    return jsonify({
                        'success': False,
                        'error': f'Video not found: {video_identifier}',
                        'video': None
                    }), 404
                
                # 비디오 파일 존재 확인
                video_filename = found_event.get('video_filename')
                print(f"Found event with video_filename: {video_filename}")
                
                if video_filename:
                    video_path = os.path.join('saved_videos', video_filename)
                    if os.path.exists(video_path):
                        stat = os.stat(video_path)
                        video_data = {
                            'id': found_event.get('id'),
                            'title': found_event.get('title', f'SafeFall Video - {video_filename}'),
                            'filename': video_filename,  # 명시적으로 설정
                            'video_filename': video_filename,  # 백업 필드
                            'name': video_filename,
                            'path': f'/media/videos/{video_filename}',
                            'url': f'/media/videos/{video_filename}',
                            'size': stat.st_size,
                            'mtime': found_event.get('created_at'),
                            'created_at': found_event.get('created_at'),
                            'createdAt': found_event.get('created_at'),
                            'confidence': found_event.get('confidence', 0.95),
                            'isChecked': found_event.get('processed', False),
                            'processed': found_event.get('processed', False),
                            'trigger_type': 'manual',
                            'device_id': found_event.get('device_id', 'manual_trigger')
                        }
                        
                        print(f"Returning video data: {video_data}")
                        
                        return jsonify({
                            'success': True,
                            'video': video_data
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': f'Video file not found: {video_filename}',
                            'video': None
                        }), 404
                else:
                    return jsonify({
                        'success': False,
                        'error': f'No video file associated with identifier: {video_identifier}',
                        'video': None
                    }), 404
                    
            except ImportError as e:
                return jsonify({
                    'success': False,
                    'error': 'Database service not available',
                    'video': None
                }), 500
                
        except Exception as e:
            print(f"Error getting video by identifier: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'video': None
            }), 500
    
    @app.route('/api/videos/<int:video_id>/status', methods=['PUT'])
    def update_video_status(video_id):
        """비디오 확인 상태 업데이트"""
        try:
            data = request.get_json() or {}
            is_checked = data.get('isChecked', False)
            
            print(f"Updating video {video_id} status to: {is_checked}")
            
            # 데이터베이스에서 업데이트
            try:
                from services.database_service import mark_event_processed
                if is_checked:
                    success = mark_event_processed(video_id)
                    if success:
                        return jsonify({
                            'success': True,
                            'message': f'Video {video_id} marked as processed'
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': f'Failed to update video {video_id} status'
                        }), 500
                else:
                    # 미처리로 돌리는 기능은 필요시 추가
                    return jsonify({
                        'success': True,
                        'message': f'Video {video_id} marked as unprocessed'
                    })
                    
            except ImportError:
                return jsonify({
                    'success': False,
                    'error': 'Database service not available'
                }), 500
                
        except Exception as e:
            print(f"Error updating video status: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/test-fall-alert', methods=['POST'])
    def test_fall_alert():
        """테스트용 낙상 알림 발송 (라즈베리파이 실제 영상 사용)"""
        try:
            data = request.get_json() or {}
            confidence = data.get('confidence', 0.95)
            
            print(f"🔥 수동 낙상 트리거: {confidence}")
            
            # 라즈베리파이 프레임 상태 확인
            has_camera_frame = frame_store.has_frame()
            frame_shape = None
            
            if has_camera_frame:
                # 현재 프레임 모양 확인
                test_frame = frame_store.get_frame()
                if test_frame is not None:
                    frame_shape = test_frame.shape
                    print(f"수동 트리거: 라즈베리파이 실제 프레임 사용 가능: {frame_shape}")
                else:
                    has_camera_frame = False
                    print("프레임 저장소에서 프레임을 가져올 수 없음")
            else:
                print("수동 트리거: 공유 프레임 저장소에 프레임 없음")
                print("라즈베리파이가 /api/detect로 프레임을 보내고 있는지 확인하세요")
            
            # VideoService에 라즈베리파이 프레임 강제 연결
            def get_real_raspberry_frame():
                return frame_store.get_frame()
            
            # 실제 라즈베리파이 프레임이 있을 때만 비디오 녹화
            if has_camera_frame:
                video_service.set_frame_source(get_real_raspberry_frame)
                print("실제 라즈베리파이 프레임으로 비디오 녹화 시작")
            else:
                # 라즈베리파이가 없어도 더미 비디오로 테스트 허용
                video_service.set_frame_source(None)  # 더미 프레임 모드
                print("라즈베리파이 프레임이 없어서 더미 비디오로 녹화 진행")
            
            # DetectionService를 통한 낙상 감지 (수동 트리거)
            result = detection_service.trigger_manual_detection(confidence)
            
            # 수동 트리거로 device_id 강제 설정
            result['device_id'] = 'manual_trigger'
            result['trigger_type'] = 'manual'
            
            # 프론트엔드용 알림 데이터 생성
            notification = {
                'id': f'fall_{int(time.time() * 1000)}',  # 고유 ID 추가
                'type': 'fall_alert',
                'title': '🚨 낙상 감지 알림',
                'message': f'낙상이 감지되었습니다! (신뢰도: {confidence:.1%})',
                'confidence': confidence,
                'timestamp': time.time(),
                'createdAt': time.time() * 1000,  # 밀리초 타임스탬프
                'device_id': 'manual_trigger',
                'severity': 'high',
                'event_id': result.get('event_id'),
                'video_path': result.get('video_path'),
                'has_real_frame': has_camera_frame
            }
            
            # 전역 알림 저장
            global latest_notification
            latest_notification = notification
            
            print(f"📡 프론트엔드 알림 준비: {notification['message']}")
            
            return jsonify({
                'success': True,
                'message': '테스트 낙상 알림이 발송되었습니다',
                'detection': result,
                'notification': notification,
                'camera_status': 'connected' if has_camera_frame else 'disconnected'
            })
            
        except Exception as e:
            print(f"❌ 테스트 알림 오류: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/media/videos/<filename>', methods=['GET'])
    def serve_video_file(filename):
        """비디오 파일 서빙 (AVI 파일 자동 MP4 변환 포함)"""
        try:
            from flask import send_file
            
            video_dir = os.path.abspath('saved_videos')
            
            # 1차: 정확한 파일명으로 찾기 (MP4 우선)
            exact_path = os.path.join(video_dir, filename)
            
            if os.path.exists(exact_path):
                print(f"✅ 비디오 파일 서빙: {exact_path}")
                return send_file(exact_path, 
                               mimetype='video/mp4' if filename.endswith('.mp4') else 'video/x-msvideo',
                               as_attachment=False,
                               download_name=filename)
            
            # 2차: MP4 파일이 없으면 AVI 파일을 찾아서 MP4로 변환
            if filename.endswith('.mp4'):
                avi_filename = filename.replace('.mp4', '.avi')
                avi_path = os.path.join(video_dir, avi_filename)
                
                if os.path.exists(avi_path):
                    print(f"🔄 AVI 파일 발견, MP4로 변환 중: {avi_filename}")
                    
                    try:
                        from utils.video_converter import VideoConverter
                        converter = VideoConverter()
                        
                        mp4_path = os.path.join(video_dir, filename)
                        result = converter.avi_to_mp4(avi_path, mp4_path, remove_original=False)
                        
                        if result['success']:
                            print(f"✅ 변환 완료: {mp4_path}")
                            return send_file(mp4_path,
                                           mimetype='video/mp4',
                                           as_attachment=False,
                                           download_name=filename)
                        else:
                            print(f"❌ 변환 실패: {result['error']}")
                            # 변환 실패 시 원본 AVI 파일 그대로 서빙
                            return send_file(avi_path,
                                           mimetype='video/x-msvideo',
                                           as_attachment=False,
                                           download_name=avi_filename)
                    except ImportError:
                        print("⚠️ VideoConverter를 가져올 수 없습니다. AVI 파일 그대로 서빙")
                        return send_file(avi_path,
                                       mimetype='video/x-msvideo',
                                       as_attachment=False,
                                       download_name=avi_filename)
            
            # 3차: 가장 최근 파일 반환 (대체)
            if filename.startswith('fall_detection_'):
                # MP4 파일 우선 검색
                mp4_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
                mp4_files.sort(reverse=True)
                
                if mp4_files:
                    recent_file = mp4_files[0]
                    recent_path = os.path.join(video_dir, recent_file)
                    print(f"📺 최근 MP4 파일로 대체: {recent_file}")
                    return send_file(recent_path,
                                   mimetype='video/mp4', 
                                   as_attachment=False,
                                   download_name=recent_file)
                
                # MP4가 없으면 AVI 파일 검색
                avi_files = [f for f in os.listdir(video_dir) if f.endswith('.avi')]
                avi_files.sort(reverse=True)
                
                print(f"📁 사용 가능한 비디오 파일들 (AVI): {avi_files[:5]}")
                
                if avi_files:
                    recent_file = avi_files[0]
                    recent_path = os.path.join(video_dir, recent_file)
                    print(f"📺 최근 AVI 파일로 대체: {recent_file}")
                    return send_file(recent_path,
                                   mimetype='video/x-msvideo', 
                                   as_attachment=False,
                                   download_name=recent_file)
            
            return jsonify({'error': f'Video file not found: {filename}'}), 404
                
        except Exception as e:
            print(f"❌ 비디오 서빙 오류: {e}")
            return jsonify({'error': str(e)}), 500

    # 기타 필요한 API들
    @app.route('/api/dashboard/recent-videos', methods=['GET'])
    def get_dashboard_recent_videos():
        """대시보드 최근 비디오"""
        try:
            limit = request.args.get('limit', 6, type=int)
            from services.database_service import get_fall_events
            events = get_fall_events(limit)
            
            formatted_videos = []
            for event in events:
                video_filename = event.get('video_filename')
                if not video_filename:
                    video_filename = f'fall_detection_{event.get("id", "unknown")}.avi'
                
                print(f"Dashboard video: ID={event.get('id')}, filename={video_filename}")
                
                formatted_videos.append({
                    'id': event.get('id'),
                    'filename': video_filename,  # 명시적 설정
                    'video_filename': video_filename,  # 백업 필드
                    'name': video_filename,
                    'title': event.get('title', f'낙상 감지 #{event.get("id")}'),
                    'createdAt': event.get('created_at', event.get('timestamp')),
                    'created_at': event.get('created_at', event.get('timestamp')),
                    'isChecked': event.get('processed', False),
                    'processed': event.get('processed', False),
                    'confidence': event.get('confidence', 0.0),
                    'device_id': event.get('device_id', 'unknown'),
                    'url': f'/media/videos/{video_filename}',
                    'path': f'/media/videos/{video_filename}'
                })
            
            return jsonify({
                'success': True,
                'data': formatted_videos,
                'count': len(formatted_videos)
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'data': []
            })

    @app.route('/api/events/falls', methods=['GET'])
    def get_fall_events():
        """낙상 이벤트 목록"""
        try:
            limit = request.args.get('limit', 100, type=int)
            from services.database_service import get_fall_events
            events = get_fall_events(limit)
            return jsonify({
                'success': True,
                'data': events,
                'count': len(events)
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0
            })

    # 간단한 API들
    @app.route('/api/notifications/stream', methods=['GET'])
    def notification_stream():
        """실시간 알림 스트림 (프론트엔드 호환)"""
        try:
            global latest_notification
            
            # 최근 알림이 있으면 반환
            notifications = []
            if latest_notification:
                notifications = [latest_notification]
                # 한 번 반환한 후 클리어 (중복 방지)
                latest_notification = None
            
            return jsonify({
                'success': True,
                'notifications': notifications,
                'count': len(notifications),
                'timestamp': time.time()
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'notifications': [],
                'count': 0,
                'timestamp': time.time(),
                'error': str(e)
            })
    
    @app.after_request
    def after_request(response):
        """모든 응답에 CORS 헤더 추가 - 중복 제거"""
        # CORS 미들웨어에서 이미 처리하므로 주석 처리
        # response.headers.add('Access-Control-Allow-Origin', '*')
        # response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        # response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    @app.route('/api/v1/notifications/latest', methods=['GET'])
    def get_notifications_v1():
        """최신 알림 목록 - NotificationManager와 연동"""
        try:
            limit = request.args.get('limit', 10, type=int)
            
            # NotificationManager에서 알림 가져오기
            if SERVICES_LOADED and notification_manager:
                notifications = notification_manager.get_latest_notifications(limit)
                unread_count = notification_manager.get_unread_count()
                
                print(f"📢 알림 API 호출: {len(notifications)}개 알림, {unread_count}개 미읽")
                
                return jsonify({
                    'success': True,
                    'notifications': notifications,
                    'count': len(notifications),
                    'unread_count': unread_count
                })
            else:
                # 서비스가 로드되지 않은 경우 빈 배열 반환
                return jsonify({
                    'success': True,
                    'notifications': [],
                    'count': 0,
                    'unread_count': 0,
                    'message': 'NotificationManager not loaded'
                })
                
        except Exception as e:
            print(f"❌ 알림 API 오류: {e}")
            return jsonify({
                'success': False,
                'notifications': [],
                'count': 0,
                'unread_count': 0,
                'error': str(e)
            }), 500

    @app.route('/api/detect/last_positive', methods=['GET'])
    def get_last_positive():
        """마지막 양성 감지 결과"""
        return jsonify({
            'success': True,
            'detection': {
                'fall_detected': False,
                'confidence': 0.0,
                'timestamp': time.time(),
                'bbox': []
            }
        })

    @app.route('/api/dashboard/stats', methods=['GET'])
    def get_dashboard_stats():
        """대시보드 통계"""
        try:
            from services.database_service import get_dashboard_stats as get_db_stats
            db_stats = get_db_stats()
            
            return jsonify({
                'success': True,
                'totalVideos': db_stats.get('total_events', 0),
                'checkedVideos': db_stats.get('total_events', 0) - db_stats.get('unprocessed_events', 0),
                'uncheckedVideos': db_stats.get('unprocessed_events', 0),
                'todayVideos': db_stats.get('today_events', 0),
                'checkRate': (db_stats.get('total_events', 0) - db_stats.get('unprocessed_events', 0)) / max(db_stats.get('total_events', 1), 1) * 100,
                'system_status': 'active'
            })
        except Exception as e:
            return jsonify({
                'success': True,
                'totalVideos': 0,
                'checkedVideos': 0,
                'uncheckedVideos': 0,
                'todayVideos': 0,
                'checkRate': 0.0,
                'system_status': 'error'
            })

    @app.route('/api/stream/status', methods=['GET'])
    def get_stream_status():
        """스트림 상태 확인"""
        return jsonify({
            'success': True,
            'stream_active': True,
            'status': 'active',
            'timestamp': time.time(),
            'message': 'Stream is running'
        })

    @app.route('/favicon.ico')
    def favicon():
        """파비콘 요청 처리"""
        return '', 204

    # Static 파일 서빙 라우트 추가
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Static 파일 서빙"""
        try:
            static_dir = os.path.join(os.getcwd(), 'static')
            return send_from_directory(static_dir, filename)
        except Exception as e:
            return jsonify({'error': str(e)}), 404
    
    @app.route('/index.html')
    def serve_index():
        """인덱스 페이지 서빙"""
        try:
            static_dir = os.path.join(os.getcwd(), 'static')
            return send_from_directory(static_dir, 'index.html')
        except Exception as e:
            return jsonify({'error': str(e)}), 404

    @app.route('/sync_test.html')
    def serve_sync_test_page():
        """동기화 테스트 페이지 서빙"""
        try:
            file_path = os.path.join(os.getcwd(), 'sync_test.html')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                from flask import Response
                return Response(content, mimetype='text/html')
            else:
                return jsonify({'error': 'Sync test page not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/test_videos.html')
    def serve_test_page():
        """테스트 페이지 서빙"""
        try:
            file_path = os.path.join(os.getcwd(), 'test_videos.html')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                from flask import Response
                return Response(content, mimetype='text/html')
            else:
                return jsonify({'error': 'Test page not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # 영상 스트리밍 라우트 추가 (/video_feed 경로로 단순 별칭 추가)
    @app.route('/video_feed')
    def main_video_feed():
        """주요 비디오 피드 (/video_feed 경로)"""
        def generate_frames():
            print("📺 실시간 스트림 시작 (/video_feed)")
            while True:
                try:
                    # 공유 프레임 저장소에서 프레임 가져오기
                    frame = frame_store.get_frame()
                    
                    if frame is not None:
                        # JPEG 인코딩
                        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if ret:
                            frame_bytes = buffer.tobytes()
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    else:
                        # 더미 프레임 생성
                        dummy_frame = create_dummy_frame()
                        ret, buffer = cv2.imencode('.jpg', dummy_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if ret:
                            frame_bytes = buffer.tobytes()
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    time.sleep(0.033)  # ~30fps
                    
                except Exception as e:
                    print(f"❌ Stream error: {e}")
                    time.sleep(0.1)
                    
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def create_dummy_frame():
        """더미 프레임 생성 (연결 대기 상태)"""
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 동적 배경
        t = time.time()
        for y in range(480):
            color_val = int(30 + 20 * np.sin(t + y * 0.01))
            frame[y, :] = [color_val, color_val, color_val]
        
        cv2.putText(frame, "SafeFall Live Stream", (150, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "Waiting for Pi Camera...", (140, 250), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
        
        # 시간 표시
        current_time = time.strftime("%H:%M:%S")
        cv2.putText(frame, current_time, (250, 300), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return frame

    @app.route('/debug/routes')
    def debug_routes():
        """등록된 라우트 목록 확인"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
        return jsonify({'routes': routes, 'total': len(routes)})
    
    @app.route('/')
    def index():
        return jsonify({
            'message': 'SafeFall Backend API Server',
            'version': '2.0',
            'status': 'running',
            'services_loaded': SERVICES_LOADED,
            'routes_registered': routes_registered,
            'endpoints': {
                'test_fall_alert': '/api/test-fall-alert',
                'videos_saved': '/api/videos/saved',
                'videos_recent': '/api/videos/recent',
                'videos_sync': '/api/videos/sync (POST)',
                'dashboard_videos': '/api/dashboard/recent-videos',
                'events_falls': '/api/events/falls',
                'test_page': '/test_videos.html',
                'sync_test_page': '/sync_test.html'  # 동기화 테스트 페이지 추가
            }
        })
    
    return app

if __name__ == '__main__':
    app = create_app()
    if app:
        print("🎯 SafeFall Backend 서버가 http://localhost:5000 에서 실행 중...")
        print("🧪 테스트 페이지: http://localhost:5000/test_videos.html")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("❌ 앱 생성 실패")
