"""영상 녹화 및 저장 전용 서비스"""
import os, time, threading, cv2, numpy as np
from datetime import datetime
from pathlib import Path
from threading import Lock
from collections import deque
from .database_service import save_fall_event

class RecordingManager:
    def __init__(self, pre=5, post=8, assumed_fps=12, max_events=200):  # post=8초로 테스트용 단축
        self.pre = pre
        self.post = post
        self.assumed_fps = assumed_fps
        self.buffer = deque(maxlen=pre*assumed_fps*3)  # 버퍼 크기 증가
        self.buffer_lock = Lock()
        self.active = False
        self.rec_lock = Lock()
        self.start_ts = None
        self.events = []
        self.event_seq = 1
        self.max_events = max_events
        self.dir = Path("recordings")
        self.dir.mkdir(exist_ok=True)
        
    def push_frame(self, ts, frame_bgr):
        """프레임 버퍼에 추가"""
        try:
            with self.buffer_lock:
                self.buffer.append((ts, frame_bgr.copy()))
        except Exception as e:
            print(f"[recording] push_frame error: {e}")
    
    def _estimate_fps(self):
        """버퍼의 프레임 타임스탬프로 FPS 추정"""
        with self.buffer_lock:
            if len(self.buffer) < 5: 
                return self.assumed_fps
            times = [t for (t,_) in self.buffer][-min(30, len(self.buffer)):]
        if len(times) < 2: 
            return self.assumed_fps
        dur = times[-1] - times[0]
        if dur <= 0: 
            return self.assumed_fps  
        fps = (len(times)-1) / dur
        return max(5, min(25, fps))
    
    def start_recording(self, confidence, device_id, trigger_reason="fall_detected"):
        """녹화 시작 (통합 DB 저장 포함)"""
        with self.rec_lock:
            if self.active:
                print("[recording] already active")
                return None
            self.active = True
            self.start_ts = time.time()
        
        # 파일명과 경로 설정
        timestamp_str = int(self.start_ts)
        filename = f"fall_event_{timestamp_str}.mp4"
        file_path = self.dir / filename
        
        # 이벤트 ID 생성 및 메모리 저장
        event_id = 1_000_000 + self.event_seq
        self.event_seq += 1
        
        event_record = {
            'id': event_id,
            'timestamp': datetime.utcfromtimestamp(self.start_ts).isoformat(),
            'video_path': str(file_path),
            'filename': filename,
            'processed': False,
            'confidence': confidence,
            'device_id': device_id,
            'trigger_reason': trigger_reason,
            'recording': True,
            'ready': False,
            'failed': False,
            'expected_end': self.start_ts + self.post,
            'duration_sec': 0,
            'filesize': 0
        }
        
        self.events.append(event_record)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # 백그라운드 녹화 스레드 시작
        recording_thread = threading.Thread(
            target=self._recording_worker, 
            args=(event_record,), 
            daemon=True
        )
        recording_thread.start()
        
        print(f"[recording] started event_id={event_id} file={filename}")
        return event_id
    
    def _recording_worker(self, event_record):
        """실제 녹화 작업 수행"""
        try:
            file_path = Path(event_record['video_path'])
            confidence = event_record['confidence']
            device_id = event_record['device_id']
            
            # Pre 프레임 수집 (감지 시점 이전)
            with self.buffer_lock:
                pre_frames = [
                    (ts, frame) for (ts, frame) in self.buffer 
                    if self.start_ts - self.pre <= ts <= self.start_ts
                ]
            
            if not pre_frames:
                print("[recording] no pre frames available")
                # 빈 프레임으로라도 시작
                dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(dummy_frame, "No Pre-Frames", (200, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                pre_frames = [(self.start_ts, dummy_frame)]
            
            # FPS 및 비디오 writer 초기화
            fps = self._estimate_fps()
            first_frame = pre_frames[0][1]
            h, w = first_frame.shape[:2]
            
            # 여러 코덱 시도
            writer = None
            for fourcc in ['mp4v', 'XVID', 'avc1']:
                writer = cv2.VideoWriter(
                    str(file_path), 
                    cv2.VideoWriter_fourcc(*fourcc), 
                    fps, (w, h)
                )
                if writer.isOpened():
                    print(f"[recording] writer opened with {fourcc}")
                    break
                writer.release()
            
            if not writer or not writer.isOpened():
                raise RuntimeError("Failed to open video writer")
            
            # Pre 프레임 기록
            frames_written = 0
            for _, frame in pre_frames:
                writer.write(frame)
                frames_written += 1
            
            last_frame = pre_frames[-1][1]
            end_time = self.start_ts + self.post
            
            # Post 프레임 기록 (실시간 수집)
            print(f"[recording] recording post frames for {self.post}s...")
            while time.time() < end_time:
                wrote_new = False
                
                # 버퍼에서 새 프레임 가져오기
                with self.buffer_lock:
                    post_frames = [
                        (ts, frame) for (ts, frame) in self.buffer 
                        if ts >= self.start_ts
                    ]
                
                # 새 프레임들 기록
                for _, frame in post_frames:
                    writer.write(frame)
                    last_frame = frame
                    frames_written += 1
                    wrote_new = True
                
                # 새 프레임이 없으면 마지막 프레임 반복
                if not wrote_new:
                    writer.write(last_frame)
                    frames_written += 1
                
                time.sleep(0.1)  # 100ms 간격
            
            # 최소 길이 보장 (1.5초)
            wall_elapsed = time.time() - self.start_ts
            min_duration = 1.5
            frame_duration = frames_written / max(fps, 1)
            actual_duration = max(wall_elapsed, frame_duration)
            
            if actual_duration < min_duration:
                padding_frames = int((min_duration - actual_duration) * fps)
                for _ in range(padding_frames):
                    writer.write(last_frame)
                    frames_written += 1
                actual_duration = min_duration
            
            writer.release()
            
            # 파일 검증 및 상태 업데이트
            if file_path.exists() and file_path.stat().st_size > 1000:
                filesize = file_path.stat().st_size
                duration = round(actual_duration, 2)
                
                # 메모리 이벤트 상태 업데이트
                event_record.update({
                    'recording': False,
                    'ready': True,
                    'failed': False,
                    'filesize': filesize,
                    'duration_sec': duration
                })
                
                # 데이터베이스에 저장
                db_event_id = save_fall_event(
                    confidence=confidence,
                    bbox=[],
                    video_path=str(file_path),
                    device_id=device_id,
                    filename=event_record['filename'],
                    duration_sec=duration,
                    trigger_reason=event_record['trigger_reason']
                )
                
                if db_event_id:
                    event_record['db_id'] = db_event_id
                    print(f"[recording] SUCCESS: event_id={event_record['id']} db_id={db_event_id} "
                          f"file={filesize}B duration={duration}s")
                else:
                    print("[recording] DB save failed but video file created")
            else:
                # 실패 상태 처리
                event_record.update({
                    'recording': False,
                    'ready': False,
                    'failed': True,
                    'error': 'Video file creation failed'
                })
                print("[recording] FAILED: video file not created or too small")
        
        except Exception as e:
            # 에러 상태 처리
            event_record.update({
                'recording': False,
                'ready': False,
                'failed': True,
                'error': str(e)
            })
            print(f"[recording] ERROR: {e}")
        
        finally:
            with self.rec_lock:
                self.active = False
                print(f"[recording] finished event_id={event_record['id']}")
    
    def get_recent_events(self, limit=20):
        """최근 녹화 이벤트 목록 반환"""
        with self.rec_lock:
            recent = sorted(
                self.events, 
                key=lambda x: x.get('timestamp', ''), 
                reverse=True
            )
            return recent[:limit]
    
    def get_event_by_id(self, event_id):
        """ID로 이벤트 조회"""
        with self.rec_lock:
            for event in self.events:
                if event['id'] == event_id:
                    return event
            return None

# 전역 녹화 매니저 인스턴스
recording_manager = RecordingManager()

# === 기존 app.py 호환성 함수들 ===
def get_video_buffer():
    """기존 video_service.py 호환"""
    with recording_manager.buffer_lock:
        return list(recording_manager.buffer)

def start_fall_recording(confidence, device_id):
    """기존 방식 호환"""
    return recording_manager.start_recording(confidence, device_id)

def is_recording_active():
    """녹화 활성 상태 확인"""
    with recording_manager.rec_lock:
        return recording_manager.active

def get_recording_status():
    """녹화 상태 정보"""
    with recording_manager.rec_lock:
        return {
            'active': recording_manager.active,
            'started_at': recording_manager.start_ts,
            'events_count': len(recording_manager.events),
            'buffer_size': recording_manager.buffer.maxlen,
            'current_buffer_frames': len(recording_manager.buffer)
        }

def register_recording_routes(app):
    """녹화 관련 API 라우트 등록"""
    
    @app.route('/api/recording/status')
    def recording_status():
        try:
            with recording_manager.rec_lock:
                return {
                    'success': True,
                    'recording_active': recording_manager.active,
                    'started_at': recording_manager.start_ts,
                    'events_count': len(recording_manager.events),
                    'recent_events': recording_manager.get_recent_events(5)
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
    
    @app.route('/api/recording/events')
    def get_recording_events():
        try:
            limit = int(request.args.get('limit', 20))
            events = recording_manager.get_recent_events(limit)
            return {'success': True, 'data': events}
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
    
    @app.route('/api/recording/video/<int:event_id>')
    def get_recording_video(event_id):
        try:
            event = recording_manager.get_event_by_id(event_id)
            if not event:
                return {'success': False, 'error': 'Event not found'}, 404
            
            video_path = event.get('video_path')
            if not video_path or not os.path.exists(video_path):
                return {'success': False, 'error': 'Video file not found'}, 404
            
            def generate():
                with open(video_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            
            from flask import Response
            response = Response(generate(), mimetype='video/mp4')
            response.headers['Content-Disposition'] = f'inline; filename="{Path(video_path).name}"'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
