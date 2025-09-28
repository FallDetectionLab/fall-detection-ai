import os
import cv2
import numpy as np
import time
import threading
from datetime import datetime

class VideoService:
    """
    - 감지 시 start_recording(seconds=30) 호출 → saved_videos/fall_detection_YYYYmmdd_HHMMSS.mp4 저장
    - 별도의 frame 공급자가 없으면 자체적으로 카메라를 열어 캡처
    - list_saved_videos() 로 저장 목록 제공
    """
    def __init__(self, save_dir="saved_videos", default_seconds=30, cam_index=0, fps=20):
        self.save_dir = save_dir
        self.default_seconds = int(default_seconds)
        self.cam_index = cam_index
        self.fps = fps
        os.makedirs(self.save_dir, exist_ok=True)

        self._recording = False
        self._lock = threading.Lock()
        self._frame_source = None   # 외부 스트리밍 핸들러가 주입 가능
        self._stop_event = threading.Event()

    # (선택) 스트리밍 핸들러에서 프레임 소스 콜백을 주입할 때 사용
    def set_frame_source(self, frame_callable):
        """
        frame_callable() -> ndarray (BGR) 또는 None
        """
        self._frame_source = frame_callable

    def _ts_filename(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.save_dir, f"fall_detection_{ts}.mp4")

    def start_recording(self, seconds=None, filename=None):
        with self._lock:
            if self._recording:
                print("이미 녹화 중입니다")
                return {"ok": False, "message": "already recording"}
            self._recording = True
            self._stop_event.clear()

        duration = int(seconds or self.default_seconds)
        save_path = filename or self._ts_filename()

        print(f"🎬 START_RECORDING 호출됨: {save_path}, {duration}초")
        print(f"🎬 현재 스레드: {threading.current_thread().name}")
        
        # 스레드로 녹화 시작
        t = threading.Thread(target=self._record_worker, args=(save_path, duration), daemon=True)
        t.start()
        print(f"🎬 녹화 스레드 시작됨: {t.name}")
        
        # 잠깐 기다린 후 녹화가 제대로 시작되었는지 확인
        time.sleep(0.1)
        
        return {"ok": True, "path": save_path, "seconds": duration}

    def stop_recording(self):
        self._stop_event.set()

    def _record_worker(self, save_path, duration):
        print(f"🎥 _record_worker 스레드 시작: {save_path}, {duration}초")
        print(f"🎥 워커 스레드: {threading.current_thread().name}")
        
        cap = None
        writer = None
        try:
            # 프레임 소스: 주입 우선, 없으면 더미 비디오 생성
            use_real_camera = False
            if self._frame_source is None:
                try:
                    cap = cv2.VideoCapture(self.cam_index)
                    if cap.isOpened():
                        # 테스트 프레임 읽어보기
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            use_real_camera = True
                            print(f"✅ 카메라 {self.cam_index} 연결 성공")
                        else:
                            cap.release()
                            cap = None
                    else:
                        cap = None
                except Exception as e:
                    print(f"⚠️ 카메라 연결 실패: {e}")
                    if cap:
                        cap.release()
                        cap = None
            
            if not use_real_camera and self._frame_source is None:
                print(f"🎥 카메라가 없어 더미 비디오를 생성합니다 ({duration}초)")

            # 기본 변수 설정
            start = time.time()
            frame_w, frame_h = 640, 480  # 고정 크기
            frame_interval = 1.0 / float(self.fps)
            next_tick = time.time()
            frame_count = 0
            
            # 코덱 선택: H.264 우선, 실패 시 fallback
            codecs_to_try = [
                ('H264', cv2.VideoWriter_fourcc(*'H264')),
                ('MJPG', cv2.VideoWriter_fourcc(*'MJPG')),  # MJPEG fallback
                ('mp4v', cv2.VideoWriter_fourcc(*'mp4v')),  # MPEG-4 fallback
                ('XVID', cv2.VideoWriter_fourcc(*'XVID'))   # Xvid fallback
            ]
            
            writer = None
            for codec_name, fourcc in codecs_to_try:
                try:
                    print(f"   🔍 {codec_name} 코덱 시도 중...")
                    test_writer = cv2.VideoWriter(save_path, fourcc, self.fps, (frame_w, frame_h))
                    
                    if test_writer.isOpened():
                        writer = test_writer
                        print(f"   ✅ {codec_name} 코덱 성공: {save_path} ({frame_w}x{frame_h}, {self.fps}fps)")
                        break
                    else:
                        test_writer.release()
                        print(f"   ❌ {codec_name} 코덱 실패")
                        
                except Exception as codec_error:
                    print(f"   ⚠️ {codec_name} 코댑 예외: {codec_error}")
                    continue
            
            if not writer or not writer.isOpened():
                raise RuntimeError(f"모든 코댑 시도 실패: {save_path}")

            # 최소 프레임 수 보장 (FPS * 시간)
            min_frames = max(self.fps * duration, 30)  # 최소 30프레임
            
            while not self._stop_event.is_set() and frame_count < min_frames:
                # 프레임 읽기
                frame = None
                
                if self._frame_source:
                    frame = self._frame_source()
                    if frame is not None:
                        print(f"라즈베리파이 실제 프레임 사용: {frame.shape}")
                    else:
                        print("프레임 소스가 None을 반환했습니다")
                elif use_real_camera and cap:
                    ok, frame = cap.read()
                    if not ok:
                        frame = None
                
                # 실제 카메라나 프레임 소스가 없으면 더미 프레임 생성
                if frame is None:
                    if self._frame_source:
                        print("프레임 소스가 있지만 None을 반환해서 더미 프레임 생성")
                    else:
                        print("프레임 소스가 없어서 더미 프레임 생성")
                    elapsed_time = frame_count / self.fps
                    frame = self._create_dummy_recording_frame(frame_count, duration, elapsed_time)
                
                # 프레임 크기 조정 (고정 크기로 맞춤)
                if frame.shape[:2] != (frame_h, frame_w):
                    frame = cv2.resize(frame, (frame_w, frame_h))

                writer.write(frame)
                frame_count += 1

                # FPS 맞추기 (실시간이 아닌 고정 간격)
                if frame_count % 10 == 0:  # 10프레임마다 진행률 출력
                    progress = (frame_count / min_frames) * 100
                    print(f"녹화 진행률: {progress:.1f}% ({frame_count}/{min_frames} 프레임)")

            actual_duration = frame_count / self.fps
            print(f"🎬 비디오 녹화 완료: {frame_count}프레임, {actual_duration:.1f}초")
            
        except Exception as e:
            print(f"[VideoService] 녹화 중 치명적 오류: {e}")
            # 오류 발생 시 부분적으로라도 파일이 있으면 삭제
            try:
                if os.path.exists(save_path) and os.path.getsize(save_path) < 1000:  # 1KB 미만이면 손상된 파일
                    os.remove(save_path)
                    print(f"손상된 파일 삭제: {save_path}")
            except:
                pass
        finally:
            # VideoWriter를 안전하게 종료 - moov atom 문제 해결
            if writer:
                try:
                    print("VideoWriter 종료 중...")
                    writer.release()
                    print("VideoWriter 종료 완료")
                    
                    # 파일이 제대로 생성되었는지 확인
                    if os.path.exists(save_path):
                        file_size = os.path.getsize(save_path)
                        print(f"생성된 비디오 파일: {save_path} ({file_size:,} bytes)")
                        
                        # OpenCV로 파일 검증
                        test_cap = cv2.VideoCapture(save_path)
                        if test_cap.isOpened():
                            test_frames = int(test_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                            test_fps = test_cap.get(cv2.CAP_PROP_FPS)
                            test_duration = test_frames / test_fps if test_fps > 0 else 0
                            print(f"비디오 검증 성공: {test_frames}프레임, {test_duration:.1f}초")
                            test_cap.release()
                            
                            # 🔥 영상 저장 완료 후 데이터베이스에 자동 기록 - 여기서 실행
                            print(f"🔥 비디오 검증 완료 후 DB 등록 시작: {save_path}")
                            try:
                                db_result = self._register_video_to_database(save_path)
                                if db_result:
                                    print(f"✅ DB 등록 성공: {save_path}")
                                else:
                                    print(f"❌ DB 등록 실패: {save_path}")
                            except Exception as db_error:
                                print(f"🔥 DB 등록 중 예외 발생: {db_error}")
                                import traceback
                                traceback.print_exc()
                        else:
                            print("경고: 생성된 비디오 파일을 열 수 없습니다")
                    else:
                        print("경고: 비디오 파일이 생성되지 않았습니다")
                        
                except Exception as release_error:
                    print(f"VideoWriter 종료 중 오류: {release_error}")
            
            if cap:
                try:
                    cap.release()
                except:
                    pass
                    
            with self._lock:
                self._recording = False
                self._stop_event.clear()
    
    def _create_dummy_recording_frame(self, frame_number, total_duration, elapsed_time=None):
        """녹화용 더미 프레임 생성 (실제 카메라처럼)"""
        if elapsed_time is None:
            elapsed_time = frame_number / self.fps if self.fps > 0 else 0
            
        # 실제 카메라처럼 보이는 프레임 생성
        frame = np.random.randint(20, 80, (480, 640, 3), dtype=np.uint8)  # 노이즈 배경
        
        # 방 내부 시뮬레이션
        # 바닥 (더 어두운 색)
        cv2.rectangle(frame, (0, 350), (640, 480), (40, 35, 30), -1)
        
        # 벽 (조금 밝은 색)
        cv2.rectangle(frame, (0, 0), (640, 350), (60, 55, 50), -1)
        
        # 가구 시뮬레이션
        # 소파
        cv2.rectangle(frame, (50, 280), (200, 350), (80, 70, 60), -1)
        # 테이블
        cv2.rectangle(frame, (300, 300), (450, 350), (90, 80, 70), -1)
        
        # 움직이는 사람 시뮬레이션
        person_x = int(100 + 300 * (elapsed_time / total_duration))  # 왼쪽에서 오른쪽으로 이동
        person_y = 320
        
        # 사람 모양 (원과 사각형)
        cv2.circle(frame, (person_x, person_y - 30), 15, (120, 100, 80), -1)  # 머리
        cv2.rectangle(frame, (person_x - 10, person_y - 15), (person_x + 10, person_y + 30), (120, 100, 80), -1)  # 몸
        
        # 낙상 시뮬레이션 (마지막 2초 동안)
        if elapsed_time > (total_duration - 2) and np.random.random() < 0.3:
            # 사람이 넘어진 모습
            cv2.ellipse(frame, (person_x, person_y + 10), (20, 8), 0, 0, 360, (120, 100, 80), -1)
            # 낙상 경고 표시
            cv2.putText(frame, "FALL DETECTED!", (180, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.rectangle(frame, (person_x - 30, person_y - 10), (person_x + 30, person_y + 20), (0, 0, 255), 3)
        
        # 카메라 정보 표시
        cv2.putText(frame, "SafeFall Camera View", (160, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # 현재 시간
        current_time = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, current_time, (450, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 프레임 카운터와 경과 시간
        cv2.putText(frame, f"Frame: {frame_number:05d}", (20, 430), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"Time: {elapsed_time:.1f}s", (20, 450), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # 녹화 진행 상태
        progress = elapsed_time / total_duration if total_duration > 0 else 0
        progress = min(1.0, progress)
        bar_width = int(300 * progress)
        cv2.rectangle(frame, (320, 420), (620, 440), (100, 100, 100), -1)
        cv2.rectangle(frame, (320, 420), (320 + bar_width, 440), (0, 255, 0), -1)
        cv2.putText(frame, f"Recording: {progress*100:.1f}%", (320, 415), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 남은 시간
        remaining = max(0, total_duration - elapsed_time)
        cv2.putText(frame, f"Remaining: {remaining:.1f}s", (450, 470), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 녹화 중 표시
        cv2.circle(frame, (600, 70), 10, (0, 0, 255), -1)
        cv2.putText(frame, "REC", (580, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        return frame
    
    def _register_video_to_database(self, video_path):
        """새로 저장된 영상을 데이터베이스에 등록"""
        print(f"🔄 데이터베이스 등록 시작: {video_path}")
        
        try:
            print("   📦 database_service import 시도...")
            from services.database_service import save_fall_event_with_video
            print("   ✅ database_service import 성공")
            
            if not os.path.exists(video_path):
                print(f"   ❌ 비디오 파일이 존재하지 않음: {video_path}")
                return False
            
            filename = os.path.basename(video_path)
            current_time = datetime.now()
            confidence = 0.95
            
            print(f"   📝 DB 등록 함수 호출: {filename}, confidence={confidence}")
            
            event_id = save_fall_event_with_video(
                timestamp=current_time,
                confidence=confidence,
                video_path=video_path
            )
            
            if event_id:
                print(f"   ✅ 데이터베이스에 영상 등록 완료: {filename} (ID: {event_id})")
                return True
            else:
                print(f"   ❌ 데이터베이스 등록 실패: {filename} (event_id가 None)")
                return False
                
        except ImportError as e:
            print(f"   ❌ 데이터베이스 서비스 import 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"   ❌ 데이터베이스 등록 중 예외 발생: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def list_saved_videos(self):
        """저장된 비디오 목록 (디스크 + DB 정보 결합)"""
        items = []
        if not os.path.isdir(self.save_dir):
            return items
            
        # 디스크에서 비디오 파일 목록 가져오기 (MP4와 AVI 모두 지원)
        video_files = {}
        for name in sorted(os.listdir(self.save_dir)):
            if not (name.lower().endswith(".mp4") or name.lower().endswith(".avi")):
                continue
            path = os.path.join(self.save_dir, name)
            stat = os.stat(path)
            video_files[name] = {
                "name": name,
                "path": f"/media/videos/{name}",
                "abs_path": os.path.abspath(path),
                "size": stat.st_size,
                "mtime": stat.st_mtime
            }
        
        # DB에서 낙상 이벤트 정보 가져오기
        try:
            from services.database_service import get_fall_events
            db_events = get_fall_events(100)  # 충분히 많이 가져오기
            
            # 비디오 파일명으로 DB 이벤트를 매핑
            db_info = {}
            for event in db_events:
                filename = event.get('video_filename')
                if filename:
                    db_info[filename] = event
                    
        except Exception as e:
            print(f"⚠️ DB 정보 가져오기 실패: {e}")
            db_info = {}
        
        # 디스크 파일과 DB 정보 결합
        for filename, file_info in video_files.items():
            event_info = db_info.get(filename, {})
            
            combined_info = {
                **file_info,
                'id': event_info.get('id'),
                'filename': filename,  # 🔥 중요: filename 필드 추가
                'video_filename': filename,  # DB 호환성
                'title': event_info.get('title', f'비디오 - {filename}'),
                'timestamp': event_info.get('timestamp'),
                'created_at': event_info.get('created_at'),
                'createdAt': event_info.get('created_at'),  # 프론트엔드 호환성
                'confidence': event_info.get('confidence', 0.0),
                'device_id': event_info.get('device_id', 'unknown'),
                'processed': event_info.get('processed', False),
                'isChecked': event_info.get('processed', False),  # 프론트엔드 호환성
                'description': event_info.get('description', ''),
                'has_db_info': bool(event_info)
            }
            
            items.append(combined_info)
            
        return items
