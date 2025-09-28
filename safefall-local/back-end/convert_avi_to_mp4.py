#!/usr/bin/env python3
"""
AVI 파일들을 MP4로 즉시 변환하는 스크립트
"""

import os
import cv2
from pathlib import Path

def convert_avi_to_mp4_simple():
    """간단한 AVI → MP4 변환"""
    
    saved_videos_dir = Path("saved_videos")
    
    if not saved_videos_dir.exists():
        print("❌ saved_videos 디렉토리가 없습니다!")
        return
    
    # AVI 파일들 찾기
    avi_files = list(saved_videos_dir.glob("*.avi"))
    
    if not avi_files:
        print("✅ 변환할 AVI 파일이 없습니다!")
        return
    
    print(f"🔄 {len(avi_files)}개의 AVI 파일을 MP4로 변환합니다...")
    
    converted = 0
    for avi_file in avi_files:
        mp4_file = avi_file.with_suffix('.mp4')
        
        # 이미 MP4가 있으면 건너뛰기
        if mp4_file.exists():
            print(f"⏩ 건너뛰기: {mp4_file.name} (이미 존재)")
            continue
        
        try:
            print(f"🔄 변환 중: {avi_file.name} → {mp4_file.name}")
            
            # OpenCV로 변환
            cap = cv2.VideoCapture(str(avi_file))
            
            if not cap.isOpened():
                print(f"❌ 파일 열기 실패: {avi_file.name}")
                continue
            
            # 비디오 정보 가져오기
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # MP4 writer 생성 (웹 호환 코덱)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(mp4_file), fourcc, fps, (width, height))
            
            if not out.isOpened():
                print(f"❌ MP4 writer 생성 실패: {mp4_file.name}")
                cap.release()
                continue
            
            # 프레임별 변환
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                out.write(frame)
                frame_count += 1
                
                # 진행률 표시
                if frame_count % 30 == 0:
                    progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
                    print(f"   진행률: {progress:.1f}%")
            
            # 정리
            cap.release()
            out.release()
            
            # 결과 확인
            if mp4_file.exists() and mp4_file.stat().st_size > 1000:
                print(f"✅ 변환 완료: {mp4_file.name} ({mp4_file.stat().st_size / (1024*1024):.1f}MB)")
                converted += 1
            else:
                print(f"❌ 변환 실패: {mp4_file.name}")
                if mp4_file.exists():
                    mp4_file.unlink()  # 실패한 파일 삭제
                    
        except Exception as e:
            print(f"❌ 변환 오류 ({avi_file.name}): {e}")
    
    print(f"\n🎉 변환 완료: {converted}개 파일")
    
    if converted > 0:
        print("✨ 이제 웹에서 영상을 재생할 수 있습니다!")
        print("🌐 프론트엔드를 새로고침하세요.")

def main():
    print("🎬 AVI → MP4 변환기")
    print("=" * 30)
    
    convert_avi_to_mp4_simple()

if __name__ == "__main__":
    main()
