#!/usr/bin/env python3
"""비디오 파일 진단 스크립트"""
import os
import cv2

def check_video_file(filepath):
    """비디오 파일 상태 확인"""
    try:
        print(f"=== 비디오 파일 검사: {filepath} ===")
        
        # 파일 존재 확인
        if not os.path.exists(filepath):
            print("❌ 파일이 존재하지 않습니다")
            return
        
        # 파일 크기 확인
        file_size = os.path.getsize(filepath)
        print(f"📊 파일 크기: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        # OpenCV로 비디오 열기 시도
        cap = cv2.VideoCapture(filepath)
        
        if not cap.isOpened():
            print("❌ OpenCV로 비디오를 열 수 없습니다")
            return
        
        # 비디오 속성 확인
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        print(f"📹 해상도: {width}x{height}")
        print(f"🎬 FPS: {fps}")
        print(f"🔢 총 프레임 수: {frame_count}")
        print(f"⏱️ 길이: {duration:.2f}초")
        
        # 첫 번째 프레임 읽기 테스트
        ret, frame = cap.read()
        if ret:
            print("✅ 첫 번째 프레임 읽기 성공")
        else:
            print("❌ 첫 번째 프레임 읽기 실패")
        
        cap.release()
        
        if duration < 1:
            print("⚠️ 경고: 비디오 길이가 너무 짧거나 0초입니다!")
            return False
        
        print("✅ 비디오 파일이 정상입니다")
        return True
        
    except Exception as e:
        print(f"❌ 검사 중 오류: {e}")
        return False

if __name__ == "__main__":
    video_dir = "saved_videos"
    
    if not os.path.exists(video_dir):
        print(f"❌ 디렉토리가 없습니다: {video_dir}")
        exit(1)
    
    # 모든 MP4 파일 검사
    mp4_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
    mp4_files.sort(reverse=True)  # 최신 파일부터
    
    print(f"📁 총 {len(mp4_files)}개의 MP4 파일 발견")
    print()
    
    # 최근 5개 파일만 검사
    for filename in mp4_files[:5]:
        filepath = os.path.join(video_dir, filename)
        check_video_file(filepath)
        print()
