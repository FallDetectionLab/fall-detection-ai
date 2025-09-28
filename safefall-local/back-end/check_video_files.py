import os

def check_video_files():
    """saved_videos 디렉토리의 실제 파일 확인"""
    video_dir = os.path.abspath('saved_videos')
    
    print(f"📁 비디오 디렉토리: {video_dir}")
    print(f"📋 디렉토리 존재 여부: {os.path.exists(video_dir)}")
    
    if os.path.exists(video_dir):
        files = os.listdir(video_dir)
        print(f"📋 총 파일 수: {len(files)}")
        
        # 비디오 파일만 필터링
        video_files = [f for f in files if f.lower().endswith(('.mp4', '.avi'))]
        print(f"🎬 비디오 파일 수: {len(video_files)}")
        
        # 최근 5개 파일 정보 출력
        print("\n📋 최근 비디오 파일들:")
        for i, filename in enumerate(sorted(video_files, reverse=True)[:5]):
            file_path = os.path.join(video_dir, filename)
            file_size = os.path.getsize(file_path)
            print(f"  {i+1}. {filename}")
            print(f"     크기: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
            print(f"     경로: {file_path}")
            print(f"     존재: {os.path.exists(file_path)}")
            
            # 특정 파일 테스트
            if filename == 'fall_detection_20250927_114000.mp4':
                print(f"     ⭐ 테스트 파일 발견!")
                print(f"     ⭐ 절대경로: {os.path.abspath(file_path)}")
    else:
        print("❌ saved_videos 디렉토리가 존재하지 않습니다!")

if __name__ == "__main__":
    check_video_files()
