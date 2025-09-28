#!/usr/bin/env python3
"""실제 카메라 연결 테스트"""
import cv2

def test_cameras():
    """사용 가능한 카메라 찾기"""
    print("사용 가능한 카메라 찾는 중...")
    
    working_cameras = []
    
    for i in range(5):  # 0~4까지 카메라 인덱스 테스트
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    working_cameras.append(i)
                    print(f"✅ 카메라 {i}: 연결됨 - 해상도 {frame.shape}")
                else:
                    print(f"❌ 카메라 {i}: 열렸지만 프레임 읽기 실패")
                cap.release()
            else:
                print(f"❌ 카메라 {i}: 연결 실패")
        except Exception as e:
            print(f"❌ 카메라 {i}: 오류 - {e}")
    
    if working_cameras:
        print(f"\n✅ 사용 가능한 카메라: {working_cameras}")
        print(f"기본 카메라 인덱스: {working_cameras[0]}")
        return working_cameras[0]
    else:
        print("\n❌ 사용 가능한 카메라가 없습니다")
        return None

if __name__ == "__main__":
    test_cameras()
