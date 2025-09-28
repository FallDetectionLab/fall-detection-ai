import cv2
import numpy as np
import os

def create_test_video():
    """웹 호환 테스트 비디오 생성"""
    output_path = os.path.join('saved_videos', 'test_web_compatible.mp4')
    
    print(f"🎬 웹 호환 테스트 비디오 생성: {output_path}")
    
    # 비디오 작성기 설정 (웹 호환 코덱 사용)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 또는 'H264'
    out = cv2.VideoWriter(output_path, fourcc, 30.0, (640, 480))
    
    if not out.isOpened():
        print("❌ 비디오 작성기 초기화 실패")
        return False
    
    # 3초간 테스트 비디오 생성
    for frame_num in range(90):  # 30fps * 3초
        # 컬러풀한 테스트 프레임 생성
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 움직이는 그라데이션 배경
        for y in range(480):
            for x in range(640):
                r = int(128 + 127 * np.sin(frame_num * 0.1 + x * 0.01))
                g = int(128 + 127 * np.sin(frame_num * 0.1 + y * 0.01))
                b = int(128 + 127 * np.sin(frame_num * 0.1 + (x+y) * 0.005))
                frame[y, x] = [b, g, r]  # BGR 순서
        
        # 텍스트 추가
        cv2.putText(frame, f"Test Video Frame {frame_num+1}", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "SafeFall Web Test", (50, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(frame, f"Time: {frame_num/30.0:.1f}s", (50, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
        
        # 움직이는 원
        center_x = int(320 + 200 * np.sin(frame_num * 0.2))
        center_y = int(240 + 100 * np.cos(frame_num * 0.2))
        cv2.circle(frame, (center_x, center_y), 50, (0, 255, 0), -1)
        
        out.write(frame)
        
        if frame_num % 30 == 0:
            print(f"   프레임 {frame_num+1}/90 생성 중...")
    
    out.release()
    
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"✅ 테스트 비디오 생성 완료!")
        print(f"   파일 크기: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"   테스트 URL: http://localhost:5000/media/videos/test_web_compatible.mp4")
        return True
    else:
        print("❌ 테스트 비디오 생성 실패")
        return False

if __name__ == "__main__":
    create_test_video()
