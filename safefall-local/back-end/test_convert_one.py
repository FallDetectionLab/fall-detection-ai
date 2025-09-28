#!/usr/bin/env python3
"""
단일 AVI 파일을 MP4로 변환하는 테스트 스크립트
"""

import os
import sys
import cv2

# 백엔드 디렉토리를 Python 경로에 추가
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def simple_avi_to_mp4(avi_path, mp4_path):
    """간단한 AVI to MP4 변환"""
    print(f"🔄 변환 시작: {avi_path} → {mp4_path}")
    
    # 원본 비디오 열기
    cap = cv2.VideoCapture(avi_path)
    if not cap.isOpened():
        print(f"❌ AVI 파일을 열 수 없습니다: {avi_path}")
        return False
    
    # 비디오 정보 가져오기
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"📹 원본 정보: {width}x{height}, {fps}fps, {total_frames}프레임")
    
    # MP4 writer 생성
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(mp4_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"❌ MP4 writer 생성 실패: {mp4_path}")
        cap.release()
        return False
    
    # 프레임별 변환
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        out.write(frame)
        frame_count += 1
        
        if frame_count % 50 == 0:
            progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
            print(f"📊 진행률: {progress:.1f}% ({frame_count}/{total_frames})")
    
    # 리소스 해제
    cap.release()
    out.release()
    
    # 결과 확인
    if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 1000:
        print(f"✅ 변환 완료: {mp4_path}")
        print(f"📁 파일 크기: {os.path.getsize(mp4_path) / (1024*1024):.1f}MB")
        return True
    else:
        print(f"❌ 변환 실패: MP4 파일이 제대로 생성되지 않았습니다")
        return False

def main():
    saved_videos_dir = os.path.join(backend_dir, 'saved_videos')
    
    if not os.path.exists(saved_videos_dir):
        print(f"❌ saved_videos 디렉토리가 없습니다: {saved_videos_dir}")
        return
    
    # AVI 파일 목록
    avi_files = [f for f in os.listdir(saved_videos_dir) if f.lower().endswith('.avi')]
    avi_files.sort(reverse=True)  # 최신 파일부터
    
    print(f"🎥 발견된 AVI 파일: {len(avi_files)}개")
    
    if not avi_files:
        print("✅ 변환할 AVI 파일이 없습니다.")
        return
    
    # 가장 최근 파일 하나만 변환
    test_avi = avi_files[0]
    test_mp4 = test_avi.replace('.avi', '.mp4')
    
    avi_path = os.path.join(saved_videos_dir, test_avi)
    mp4_path = os.path.join(saved_videos_dir, test_mp4)
    
    print(f"🧪 테스트 변환: {test_avi}")
    
    # 이미 MP4가 있으면 건너뛰기
    if os.path.exists(mp4_path):
        print(f"⏩ MP4 파일이 이미 있습니다: {test_mp4}")
        return
    
    # 변환 실행
    success = simple_avi_to_mp4(avi_path, mp4_path)
    
    if success:
        print("🎉 테스트 변환이 성공했습니다!")
        print(f"🌐 웹에서 확인: http://localhost:5000/media/videos/{test_mp4}")
    else:
        print("😞 테스트 변환이 실패했습니다.")

if __name__ == "__main__":
    main()
