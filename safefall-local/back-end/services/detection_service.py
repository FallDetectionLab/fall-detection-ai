# services/detection_service.py

from typing import Optional, Dict, Any
import time

class DetectionService:
    def __init__(self, *args, **kwargs):
        # ... (기존 초기화 코드가 있다면 그대로 유지)
        self.video_service = None              # ✅ 정석: 속성 보장
        self.notification_manager = None       # ✅ 알림 주입 지점(있다면)
        # self.db = ...                        # (있다면 유지)

    # === 주입 메서드들 ===
    def set_video_service(self, video_service):
        """VideoService 주입 (낙상 확정 시 녹화 트리거용)"""
        self.video_service = video_service

    def set_notification_manager(self, manager):
        """NotificationManager 주입(있을 경우)"""
        self.notification_manager = manager

    # === 공개 API: 수동 트리거(기존 라우트에서 호출 중) ===
    def trigger_manual_detection(self, confidence: float = 0.9) -> Dict[str, Any]:
        """
        수동 트리거: 데모/테스트용. confidence가 임계값 이상이면 '낙상'으로 간주.
        """
        fall_detected = bool(confidence >= 0.9)
        result = {
            "event_id": None,     # 필요시 DB 연동해 ID 발급
            "fall_detected": fall_detected,
            "confidence": confidence,
            "timestamp": time.time(),
            "bbox": [],
            "device_id": "manual"
        }
        # 낙상 확정 처리(녹화/알림/DB 등)
        self.handle_detection_result(result)
        return result

    # === 공개 API: /api/detect 본문을 여기로 전달해 처리 ===
    def handle_detect_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        라우트에서 받은 JSON payload를 표준 결과로 정규화하고
        낙상 확정 시 각 서비스(영상/알림/DB)를 호출.
        """
        fall = bool(payload.get("fall_detected", False))
        confidence = float(payload.get("confidence", 0.0))
        bbox = payload.get("bbox", [])
        device_id = payload.get("device_id", "unknown")

        result = {
            "event_id": None,            # 필요시 DB에서 생성
            "fall_detected": fall,
            "confidence": confidence,
            "timestamp": time.time(),
            "bbox": bbox,
            "device_id": device_id
        }
        self.handle_detection_result(result)
        return result

    # === 내부 공통 처리: 낙상 확정 시 해야 할 일들을 한 곳에서 ===
    def handle_detection_result(self, result: Dict[str, Any]) -> None:
        """
        낙상 확정/부정 모두 여기로 들어옴.
        - True면: 영상 녹화 트리거, 알림, DB 기록 등
        - False면: 필요 시 통계/로그만
        """
        fall = bool(result.get("fall_detected", False))
        confidence = float(result.get("confidence", 0.0))
        device_id = result.get("device_id", "unknown")
        timestamp = result.get("timestamp", time.time())

        print(f"🔍 감지 결과 처리 - 낙상: {fall}, 신뢰도: {confidence:.2f}, 장치: {device_id}")

        # 1) 낙상일 때만 녹화 트리거
        if fall and self.video_service:
            try:
                print("🎬 낙상 감지! 비디오 녹화 시작...")
                record_result = self.video_service.start_recording()  # 기본 30초
                result["video_recorded"] = record_result.get("ok", False)
                result["video_path"] = record_result.get("path", None)
                print(f"✅ 녹화 시작됨: {record_result}")
            except Exception as e:
                print(f"[DetectionService] start_recording 실패: {e}")
                result["video_recorded"] = False

        # 2) 낙상일 때 알림 발송
        if fall and self.notification_manager:
            try:
                print("📢 낙상 감지! 알림 발송 시작...")
                notification = self.notification_manager.add_fall_notification(
                    confidence=confidence,
                    timestamp=timestamp,
                    device_id=device_id,
                    event_id=result.get("event_id")
                )
                result["notification_sent"] = True
                result["notification_id"] = notification.get("id")
                print(f"✅ 알림 발송 완료: {notification.get('message')}")
            except Exception as e:
                print(f"[DetectionService] 알림 발송 실패: {e}")
                result["notification_sent"] = False

        # 3) DB 기록은 VideoService에서 녹화 완료 후 자동으로 처리됨
        # DetectionService에서는 DB 저장하지 않음 (중복 방지)
        try:
            if fall:
                print(f"낙상 감지됨 - VideoService에서 녹화 완료 후 자동으로 DB 등록될 예정")
                result["db_saved"] = "pending"  # VideoService에서 처리됨
            else:
                result["db_saved"] = False
        except Exception as e:
            print(f"[DetectionService] 감지 결과 처리 오류: {e}")
            result["db_saved"] = False

        print(f"✅ 감지 결과 처리 완료: {result}")

    # === API 라우트에서 호출하는 메서드들 ===
    def process_frame(self, frame, device_id="unknown", frame_number=0) -> Dict[str, Any]:
        """
        라즈베리파이에서 받은 프레임을 처리하여 낙상 감지 수행
        실제 AI 모델이 있다면 여기서 추론 수행
        현재는 자동 감지 비활성화 (수동 트리거만 사용)
        """
        # 자동 감지 비활성화 - 항상 낙상 없음으로 반환
        result = {
            "fall_detected": False,  # 자동 감지 비활성화
            "confidence": 0.0,
            "bbox": [],
            "timestamp": time.time(),
            "device_id": device_id,
            "frame_number": frame_number
        }
        
        # 실제 AI 모델이 있다면 여기서 추론 수행:
        # model_result = self.ai_model.predict(frame)
        # result["fall_detected"] = model_result.fall_detected
        # result["confidence"] = model_result.confidence
        # result["bbox"] = model_result.bbox
        
        return result
    
    def get_last_positive_detection(self) -> Optional[Dict[str, Any]]:
        """
        마지막 양성 감지 결과 반환
        """
        # 실제로는 DB나 메모리에서 마지막 양성 결과를 가져와야 함
        return {
            "fall_detected": False,
            "confidence": 0.0,
            "timestamp": time.time(),
            "bbox": []
        }
