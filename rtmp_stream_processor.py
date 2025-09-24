#!/usr/bin/env python3
"""
RTMP 스트림을 받아서 실시간 낙상 감지하는 백엔드 코드
라즈베리파이 → EC2 RTMP → 프레임 추출 → YOLO 감지 → DB 저장
"""

import cv2
import numpy as np
import threading
import time
from datetime import datetime, timedelta
from collections import deque
import os
import requests

# 기존 모듈들
from detection.infer import load_yolo_v8, infer_with_v8_model
from services.notification_service import create_notification
from sf_models.entities import db, Event

class RTMPStreamProcessor:
    """
    RTMP 스트림을 받아서 실시간으로 낙상 감지하는 클래스
    """
    
    def __init__(self, rtmp_url="rtmp://localhost/live/stream"):
        self.rtmp_url = rtmp_url
        self.is_running = False
        self.yolo_model = None
        self.yolo_names = None
        
        # 30초 영상 저장을 위한 프레임 버퍼 (30fps * 30초 = 900프레임)
        self.frame_buffer = deque(maxlen=900)  # 30초 버퍼
        self.fps = 30
        
        # 낙상 감지 설정
        self.fall_detection_cooldown = 10  # 10초 쿨다운
        self.last_fall_time = 0
        
        print(f"🎥 RTMP 스트림 프로세서 초기화: {rtmp_url}")
    
    def initialize_yolo(self):
        """
        YOLO 모델 초기화
        """
        try:
            weights_path = os.getenv("YOLO_WEIGHTS", "/srv/flaskapp/best.pt")
            print(f"📊 YOLO 모델 로딩: {weights_path}")
            
            self.yolo_model, self.yolo_names = load_yolo_v8(weights_path)
            print("✅ YOLO 모델 로딩 완료")
            return True
            
        except Exception as e:
            print(f"❌ YOLO 모델 로딩 실패: {e}")
            return False
    
    def connect_rtmp_stream(self):
        """
        RTMP 스트림 연결
        """
        print(f"🔗 RTMP 스트림 연결 시도: {self.rtmp_url}")
        
        # OpenCV로 RTMP 스트림 연결
        cap = cv2.VideoCapture(self.rtmp_url)
        
        if not cap.isOpened():
            print("❌ RTMP 스트림 연결 실패")
            return None
        
        # 스트림 정보 확인
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"✅ RTMP 스트림 연결 성공")
        print(f"   해상도: {width}x{height}")
        print(f"   FPS: {fps}")
        
        self.fps = max(fps, 15)  # 최소 15fps
        return cap
    
    def save_fall_video(self, fall_frame_index):
        """
        낙상 감지 시 앞뒤 30초 영상 저장
        """
        try:
            if len(self.frame_buffer) < 300:  # 10초 미만의 버퍼면 저장 안함
                print("⚠️  프레임 버퍼가 부족하여 영상 저장 불가")
                return None
            
            # 타임스탬프 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fall_{timestamp}.mp4"
            filepath = f"/tmp/{filename}"  # 임시 저장
            
            print(f"💾 낙상 영상 저장 시작: {filename}")
            
            # 프레임 버퍼에서 영상 생성
            frames = list(self.frame_buffer)
            if not frames:
                return None
            
            # 영상 작성기 초기화
            height, width = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(filepath, fourcc, self.fps, (width, height))
            
            # 모든 버퍼 프레임을 영상으로 저장
            for frame in frames:
                out.write(frame)
            
            out.release()
            
            print(f"✅ 낙상 영상 저장 완료: {filepath}")
            
            # DB에 이벤트 기록
            self.save_fall_event(filename, filepath)
            
            return filepath
            
        except Exception as e:
            print(f"❌ 낙상 영상 저장 실패: {e}")
            return None
    
    def save_fall_event(self, filename, filepath):
        """
        낙상 이벤트를 DB에 저장
        """
        try:
            # Event 테이블에 기록
            event = Event(
                device_id="rtmp_stream",
                path=filename,
                type="fall"
            )
            
            db.session.add(event)
            db.session.commit()
            
            print(f"📝 낙상 이벤트 DB 저장 완료 (ID: {event.id})")
            
            # 알림 전송
            create_notification(
                title="🚨 낙상 감지 알림",
                message=f"RTMP 스트림에서 낙상이 감지되었습니다. 영상이 저장되었습니다: {filename}",
                notification_type="fall_detected",
                severity="high"
            )
            
        except Exception as e:
            print(f"❌ DB 저장 실패: {e}")
    
    def process_frame(self, frame):
        """
        개별 프레임에서 낙상 감지
        """
        try:
            if self.yolo_model is None:
                return False
            
            # 프레임을 JPEG로 인코딩
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                return False
            
            frame_bytes = buffer.tobytes()
            
            # YOLO 추론
            detections = infer_with_v8_model(
                model=self.yolo_model,
                image_bytes=frame_bytes,
                class_names=self.yolo_names,
                imgsz=640,
                device="cpu"
            )
            
            # 낙상 감지 확인
            fall_detected = False
            for det in detections:
                # "item" 클래스를 "fall"로 매핑 (기존 코드와 동일)
                if det.get("label") == "item":
                    det["label"] = "fall"
                
                if det.get("label") == "fall" and det.get("conf", 0) > 0.4:
                    fall_detected = True
                    confidence = det.get("conf", 0)
                    print(f"🚨 낙상 감지! 신뢰도: {confidence:.2f}")
                    break
            
            return fall_detected
            
        except Exception as e:
            print(f"❌ 프레임 처리 오류: {e}")
            return False
    
    def run_stream_processing(self):
        """
        메인 스트림 처리 루프
        """
        print("🚀 RTMP 스트림 처리 시작")
        
        # YOLO 모델 초기화
        if not self.initialize_yolo():
            print("❌ YOLO 초기화 실패, 처리 중단")
            return
        
        # RTMP 스트림 연결
        cap = self.connect_rtmp_stream()
        if cap is None:
            print("❌ RTMP 연결 실패, 처리 중단")
            return
        
        self.is_running = True
        frame_count = 0
        fall_count = 0
        
        print("📹 프레임 처리 루프 시작...")
        
        try:
            while self.is_running:
                ret, frame = cap.read()
                
                if not ret:
                    print("⚠️  프레임 읽기 실패, 재연결 시도...")
                    cap.release()
                    time.sleep(2)
                    cap = self.connect_rtmp_stream()
                    if cap is None:
                        break
                    continue
                
                frame_count += 1
                
                # 프레임 버퍼에 추가 (30초 보관)
                self.frame_buffer.append(frame.copy())
                
                # 낙상 감지 처리 (매 프레임마다)
                current_time = time.time()
                if current_time - self.last_fall_time > self.fall_detection_cooldown:
                    
                    if self.process_frame(frame):
                        fall_count += 1
                        self.last_fall_time = current_time
                        
                        # 30초 영상 저장
                        saved_path = self.save_fall_video(frame_count)
                        if saved_path:
                            print(f"💾 낙상 영상 저장됨: {saved_path}")
                
                # 5초마다 상태 출력
                if frame_count % (self.fps * 5) == 0:
                    elapsed_time = frame_count / self.fps
                    print(f"📊 처리 상태: {frame_count}프레임, {elapsed_time:.1f}초, 낙상감지: {fall_count}회")
                
                # CPU 부하 조절
                time.sleep(1 / self.fps)
                
        except KeyboardInterrupt:
            print("\n⏹️  사용자에 의해 중단됨")
            
        except Exception as e:
            print(f"❌ 스트림 처리 오류: {e}")
            
        finally:
            self.is_running = False
            if cap:
                cap.release()
            print("🔚 RTMP 스트림 처리 종료")
    
    def start_background_processing(self):
        """
        백그라운드에서 스트림 처리 시작
        """
        if self.is_running:
            print("⚠️  이미 처리 중입니다")
            return
        
        self.processing_thread = threading.Thread(
            target=self.run_stream_processing,
            daemon=True
        )
        self.processing_thread.start()
        print("🧵 백그라운드 스트림 처리 시작됨")
    
    def stop_processing(self):
        """
        스트림 처리 중지
        """
        if self.is_running:
            self.is_running = False
            print("⏹️  스트림 처리 중지 중...")


# 전역 인스턴스
rtmp_processor = None

def start_rtmp_processing():
    """
    RTMP 처리 시작 함수 (Flask 앱에서 호출)
    """
    global rtmp_processor
    
    if rtmp_processor is None:
        # RTMP URL 설정 (라즈베리파이에서 오는 스트림)
        rtmp_url = "rtmp://localhost/live/stream"
        rtmp_processor = RTMPStreamProcessor(rtmp_url)
    
    rtmp_processor.start_background_processing()

def stop_rtmp_processing():
    """
    RTMP 처리 중지 함수
    """
    global rtmp_processor
    
    if rtmp_processor:
        rtmp_processor.stop_processing()

# Flask 앱에서 사용할 엔드포인트
def create_rtmp_routes(app):
    """
    RTMP 관련 라우트 생성
    """
    
    @app.get("/api/v1/rtmp/status")
    def get_rtmp_status():
        if rtmp_processor and rtmp_processor.is_running:
            return {"status": "running", "message": "RTMP 스트림 처리 중"}
        else:
            return {"status": "stopped", "message": "RTMP 스트림 처리 중지됨"}
    
    @app.post("/api/v1/rtmp/start")
    def start_rtmp():
        try:
            start_rtmp_processing()
            return {"ok": True, "message": "RTMP 처리 시작됨"}
        except Exception as e:
            return {"ok": False, "error": str(e)}, 500
    
    @app.post("/api/v1/rtmp/stop")
    def stop_rtmp():
        try:
            stop_rtmp_processing()
            return {"ok": True, "message": "RTMP 처리 중지됨"}
        except Exception as e:
            return {"ok": False, "error": str(e)}, 500

if __name__ == "__main__":
    # 테스트용 직접 실행
    processor = RTMPStreamProcessor()
    processor.run_stream_processing()
