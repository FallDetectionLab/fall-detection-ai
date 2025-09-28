import cv2
import os
import numpy as np

def create_reliable_web_videos():
    """확실히 웹에서 재생되는 비디오들 생성"""
    video_dir = 'saved_videos'
    
    print("🎬 확실한 웹 호환 비디오들 생성...")
    
    # 여러 가지 방법으로 테스트 비디오 생성
    methods = [
        ('MJPG', cv2.VideoWriter_fourcc(*'MJPG'), '.avi'),
        ('mp4v', cv2.VideoWriter_fourcc(*'mp4v'), '.mp4'),
        ('XVID', cv2.VideoWriter_fourcc(*'XVID'), '.avi'),
        ('H264', cv2.VideoWriter_fourcc(*'H264'), '.mp4'),
        ('avc1', cv2.VideoWriter_fourcc(*'avc1'), '.mp4'),
    ]
    
    successful_files = []
    
    for method_name, fourcc, extension in methods:
        output_path = os.path.join(video_dir, f'web_reliable_{method_name.lower()}{extension}')
        
        print(f"\n📹 {method_name} 코덱으로 생성 중...")
        
        try:
            # VideoWriter 생성
            out = cv2.VideoWriter(output_path, fourcc, 30.0, (640, 480))
            
            if not out.isOpened():
                print(f"   ❌ {method_name} VideoWriter 초기화 실패")
                continue
            
            # 30프레임 (1초) 간단한 비디오 생성
            for frame_num in range(30):
                # 컬러풀한 테스트 프레임
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # 그라데이션 배경
                for y in range(480):
                    for x in range(640):
                        frame[y, x, 0] = (x * 255) // 640  # Blue
                        frame[y, x, 1] = (y * 255) // 480  # Green
                        frame[y, x, 2] = ((x + y) * 255) // (640 + 480)  # Red
                
                # 텍스트 추가
                cv2.putText(frame, f"{method_name} Test", (200, 200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
                cv2.putText(frame, f"Frame {frame_num+1}/30", (200, 300), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # 움직이는 원
                center_x = int(320 + 100 * np.sin(frame_num * 0.2))
                center_y = int(240 + 50 * np.cos(frame_num * 0.3))
                cv2.circle(frame, (center_x, center_y), 30, (0, 255, 255), -1)
                
                out.write(frame)
            
            out.release()
            
            # 파일 검증
            if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
                file_size = os.path.getsize(output_path)
                print(f"   ✅ {method_name} 성공! 크기: {file_size:,} bytes")
                
                # OpenCV로 재검증
                cap = cv2.VideoCapture(output_path)
                if cap.isOpened():
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    cap.release()
                    print(f"     검증: {frame_count}프레임, {fps:.1f}fps")
                    
                    successful_files.append({
                        'name': os.path.basename(output_path),
                        'method': method_name,
                        'size': file_size,
                        'frames': frame_count,
                        'url': f'http://localhost:5000/media/videos/{os.path.basename(output_path)}'
                    })
                else:
                    print(f"   ❌ {method_name} 재검증 실패")
            else:
                print(f"   ❌ {method_name} 파일 생성 실패")
                if os.path.exists(output_path):
                    os.remove(output_path)
                    
        except Exception as e:
            print(f"   ❌ {method_name} 오류: {e}")
    
    print(f"\n🎯 생성 완료! 성공한 파일: {len(successful_files)}개")
    
    if successful_files:
        print("\n📋 성공한 파일들:")
        for file_info in successful_files:
            print(f"   - {file_info['name']} ({file_info['method']})")
            print(f"     크기: {file_info['size']:,} bytes")
            print(f"     URL: {file_info['url']}")
    
    return successful_files

def create_minimal_mp4():
    """최소한의 MP4 파일 생성 (웹 호환성 최우선)"""
    output_path = os.path.join('saved_videos', 'minimal_web.mp4')
    
    print(f"\n🎬 최소한의 웹 호환 MP4 생성: {output_path}")
    
    # mp4v 코덱으로 최소한의 파일 생성
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 30.0, (320, 240))  # 작은 해상도
    
    if not out.isOpened():
        print("❌ MP4 작성기 초기화 실패")
        return False
    
    # 15프레임 (0.5초) 매우 간단한 비디오
    for i in range(15):
        # 단색 프레임
        frame = np.full((240, 320, 3), [100, 150, 200], dtype=np.uint8)
        
        # 간단한 텍스트
        cv2.putText(frame, f"{i+1}", (150, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        out.write(frame)
    
    out.release()
    
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"✅ 최소 MP4 생성 완료! 크기: {file_size:,} bytes")
        print(f"🌐 URL: http://localhost:5000/media/videos/minimal_web.mp4")
        return True
    else:
        print("❌ 최소 MP4 생성 실패")
        return False

if __name__ == "__main__":
    print("🎬 확실한 웹 호환 비디오 생성 도구")
    print("=" * 60)
    
    # 1. 여러 방법으로 테스트 비디오 생성
    successful_files = create_reliable_web_videos()
    
    # 2. 최소한의 MP4 생성
    print("\n" + "=" * 60)
    minimal_success = create_minimal_mp4()
    
    print(f"\n🎯 최종 결과:")
    print(f"   다양한 코덱 테스트: {len(successful_files)}개 성공")
    print(f"   최소 MP4: {'✅ 성공' if minimal_success else '❌ 실패'}")
    
    if successful_files or minimal_success:
        print(f"\n🌐 React 앱에서 테스트할 URL들:")
        for file_info in successful_files:
            print(f"   {file_info['url']}")
        if minimal_success:
            print(f"   http://localhost:5000/media/videos/minimal_web.mp4")
