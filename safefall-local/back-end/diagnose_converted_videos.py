import os
import cv2

def check_converted_videos():
    """변환된 비디오 파일들 상태 확인"""
    video_dir = 'saved_videos'
    
    print("🔍 변환된 비디오 파일들 확인...")
    
    # web_ 접두사가 붙은 파일들 찾기
    web_files = [f for f in os.listdir(video_dir) if f.startswith('web_') and f.endswith('.mp4')]
    
    if not web_files:
        print("❌ web_ 접두사가 붙은 변환 파일이 없습니다!")
        return
    
    print(f"📋 변환된 파일 수: {len(web_files)}")
    
    for filename in web_files[:5]:  # 처음 5개만 확인
        file_path = os.path.join(video_dir, filename)
        
        print(f"\n🎬 {filename} 확인:")
        
        # 파일 크기 확인
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"   크기: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            
            if file_size < 1000:
                print("   ❌ 파일이 너무 작습니다 (손상된 파일)")
                continue
        else:
            print("   ❌ 파일이 존재하지 않습니다")
            continue
        
        # 파일 헤더 확인
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
                print(f"   헤더: {header.hex()}")
                if b'ftyp' in header:
                    print("   ✅ 유효한 MP4 시그니처")
                else:
                    print("   ❌ 잘못된 MP4 시그니처")
        except Exception as e:
            print(f"   ❌ 헤더 읽기 실패: {e}")
        
        # OpenCV로 파일 검증
        try:
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration = frame_count / fps if fps > 0 else 0
                
                print(f"   ✅ OpenCV 검증 성공:")
                print(f"     해상도: {width}x{height}")
                print(f"     FPS: {fps:.1f}")
                print(f"     프레임: {frame_count}")
                print(f"     길이: {duration:.1f}초")
                
                # 첫 번째 프레임 읽기 테스트
                ret, frame = cap.read()
                if ret:
                    print("   ✅ 첫 프레임 읽기 성공")
                else:
                    print("   ❌ 첫 프레임 읽기 실패")
                
                cap.release()
            else:
                print("   ❌ OpenCV로 파일을 열 수 없습니다")
        except Exception as e:
            print(f"   ❌ OpenCV 검증 실패: {e}")
        
        print(f"   🌐 테스트 URL: http://localhost:5000/media/videos/{filename}")

def recreate_simple_web_video():
    """간단한 웹 호환 비디오 재생성"""
    output_path = os.path.join('saved_videos', 'simple_web_test.mp4')
    
    print(f"\n🎬 간단한 웹 호환 비디오 재생성: {output_path}")
    
    # 가장 기본적인 MP4V 코덱 사용
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 30.0, (640, 480))
    
    if not out.isOpened():
        print("❌ VideoWriter 초기화 실패")
        return False
    
    # 60프레임 (2초) 간단한 비디오 생성
    for frame_num in range(60):
        # 단순한 컬러 프레임
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 빨간색 배경
        frame[:, :, 2] = 200
        
        # 프레임 번호 텍스트
        cv2.putText(frame, f"Frame {frame_num+1}/60", (200, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        out.write(frame)
        
        if frame_num % 20 == 0:
            print(f"   진행: {frame_num+1}/60")
    
    out.release()
    
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"✅ 간단한 비디오 생성 완료! 크기: {file_size:,} bytes")
        print(f"🌐 테스트 URL: http://localhost:5000/media/videos/simple_web_test.mp4")
        return True
    else:
        print("❌ 간단한 비디오 생성 실패")
        return False

if __name__ == "__main__":
    import numpy as np
    
    print("🔍 변환된 비디오 파일 진단 도구")
    print("=" * 50)
    
    # 1. 변환된 파일들 확인
    check_converted_videos()
    
    # 2. 간단한 웹 호환 비디오 재생성
    print("\n" + "=" * 50)
    recreate_simple_web_video()
