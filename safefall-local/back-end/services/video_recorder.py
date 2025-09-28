import cv2
import os
import time
import threading
from datetime import datetime
from collections import deque
import numpy as np

class VideoRecorder:
    def __init__(self, buffer_seconds=5, post_record_seconds=10):
        """
        buffer_seconds: 낙상 감지 전 몇 초간의 영상을 저장할지
        post_record_seconds: 낙상 감지 후 몇 초간 더 녹화할지
        """
        self.buffer_seconds = buffer_seconds
        self.post_record_seconds = post_record_seconds
        self.fps = 30  # 기본 FPS
        
        # 프레임 버퍼 (낙상 감지 전 영상 저장용)
        self.frame_buffer = deque(maxlen=buffer_seconds * self.fps)
        self.buffer_lock = threading.Lock()
        
        # 저장 디렉토리 설정
        self.save_directory = os.path.join(os.path.dirname(__file__), '..', 'saved_videos')
        os.makedirs(self.save_directory, exist_ok=True)
        
        # 현재 녹화 상태
        self.is_recording = False
        self.current_writer = None
        self.recording_thread = None
        
        print(f"📹 VideoRecorder 초기화 완료 - 저장 경로: {self.save_directory}")
    
    def add_frame(self, frame):
        """실시간으로 들어오는 프레임을 버퍼에 추가"""
        if frame is not None:
            timestamp = time.time()
            with self.buffer_lock:
                self.frame_buffer.append((frame.copy(), timestamp))
    
    def start_fall_recording(self, fall_data=None):
        """낙상 감지 시 녹화 시작"""
        if self.is_recording:
            print("⚠️ 이미 녹화 중입니다")
            return None
        
        # 파일명 생성 (타임스탬프 기반)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fall_detection_{timestamp}.mp4"
        filepath = os.path.join(self.save_directory, filename)
        
        # 녹화 스레드 시작
        self.recording_thread = threading.Thread(
            target=self._record_fall_video,
            args=(filepath, fall_data),
            daemon=True
        )
        
        self.is_recording = True
        self.recording_thread.start()
        
        print(f"🎬 낙상 영상 녹화 시작: {filename}")
        return filepath
    
    def _record_fall_video(self, filepath, fall_data):
        """실제 영상 저장 로직"""
        try:
            # 버퍼에서 프레임들 가져오기
            with self.buffer_lock:
                buffered_frames = list(self.frame_buffer)
            
            if not buffered_frames:
                print("❌ 저장할 프레임이 없습니다")
                self.is_recording = False
                return
            
            # 첫 번째 프레임으로 비디오 설정 확인
            first_frame = buffered_frames[0][0]
            height, width = first_frame.shape[:2]
            
            # VideoWriter 초기화
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.current_writer = cv2.VideoWriter(
                filepath, fourcc, self.fps, (width, height)
            )
            
            if not self.current_writer.isOpened():
                print(f"❌ VideoWriter 초기화 실패: {filepath}")
                self.is_recording = False
                return
            
            # 1. 버퍼된 프레임들 먼저 저장 (낙상 감지 전)
            for frame, timestamp in buffered_frames:
                self.current_writer.write(frame)
            
            print(f"📼 버퍼 프레임 {len(buffered_frames)}개 저장 완료")
            
            # 2. 낙상 감지 후 추가 녹화
            start_time = time.time()
            frame_count = 0
            
            while time.time() - start_time < self.post_record_seconds:
                # 실시간 프레임 계속 저장
                with self.buffer_lock:
                    if self.frame_buffer:
                        latest_frame, _ = self.frame_buffer[-1]
                        self.current_writer.write(latest_frame)
                        frame_count += 1
                
                time.sleep(1/self.fps)  # FPS에 맞춰 대기
            
            print(f"📹 낙상 후 프레임 {frame_count}개 추가 저장")
            
            # 3. 영상 메타데이터 저장
            self._save_video_metadata(filepath, fall_data, len(buffered_frames) + frame_count)
            
        except Exception as e:
            print(f"❌ 영상 저장 중 오류: {e}")
        finally:
            # 정리
            if self.current_writer:
                self.current_writer.release()
                self.current_writer = None
            
            self.is_recording = False
            print(f"✅ 영상 저장 완료: {os.path.basename(filepath)}")
    
    def _save_video_metadata(self, filepath, fall_data, total_frames):
        """영상과 함께 메타데이터 저장"""
        metadata = {
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'timestamp': datetime.now().isoformat(),
            'total_frames': total_frames,
            'duration_seconds': total_frames / self.fps,
            'fps': self.fps,
            'fall_data': fall_data or {},
            'file_size': os.path.getsize(filepath) if os.path.exists(filepath) else 0
        }
        
        # JSON 파일로 메타데이터 저장
        metadata_path = filepath.replace('.mp4', '_metadata.json')
        try:
            import json
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"📄 메타데이터 저장: {os.path.basename(metadata_path)}")
        except Exception as e:
            print(f"⚠️ 메타데이터 저장 실패: {e}")
    
    def get_saved_videos(self):
        """저장된 영상 목록 반환"""
        videos = []
        if not os.path.exists(self.save_directory):
            return videos
        
        for filename in os.listdir(self.save_directory):
            if filename.endswith('.mp4'):
                filepath = os.path.join(self.save_directory, filename)
                metadata_path = filepath.replace('.mp4', '_metadata.json')
                
                video_info = {
                    'filename': filename,
                    'filepath': filepath,
                    'size': os.path.getsize(filepath),
                    'created': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                }
                
                # 메타데이터가 있으면 추가
                if os.path.exists(metadata_path):
                    try:
                        import json
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        video_info.update(metadata)
                    except:
                        pass
                
                videos.append(video_info)
        
        # 생성 시간 역순 정렬
        videos.sort(key=lambda x: x['created'], reverse=True)
        return videos
    
    def cleanup_old_videos(self, max_videos=50):
        """오래된 영상 파일 정리"""
        videos = self.get_saved_videos()
        if len(videos) <= max_videos:
            return
        
        # 오래된 영상들 삭제
        for video in videos[max_videos:]:
            try:
                os.remove(video['filepath'])
                # 메타데이터 파일도 삭제
                metadata_path = video['filepath'].replace('.mp4', '_metadata.json')
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
                print(f"🗑️ 오래된 영상 삭제: {video['filename']}")
            except Exception as e:
                print(f"⚠️ 영상 삭제 실패: {e}")
