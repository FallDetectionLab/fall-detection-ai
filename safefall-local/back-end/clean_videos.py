#!/usr/bin/env python3
"""손상된 비디오 파일 정리 스크립트"""
import os
import cv2

def clean_corrupted_videos():
    """손상된 비디오 파일들을 삭제"""
    video_dir = "saved_videos"
    
    if not os.path.exists(video_dir):
        print(f"❌ 디렉토리가 없습니다: {video_dir}")
        return
    
    mp4_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
    print(f"📁 총 {len(mp4_files)}개의 MP4 파일 검사 중...")
    
    deleted_count = 0
    
    for filename in mp4_files:
        filepath = os.path.join(video_dir, filename)
        
        try:
            # 파일 크기 확인
            file_size = os.path.getsize(filepath)
            
            # 너무 작은 파일들 (1KB 미만)
            if file_size < 1000:
                print(f"🗑️ 삭제: {filename} (크기: {file_size} bytes - 너무 작음)")
                os.remove(filepath)
                deleted_count += 1
                continue
            
            # OpenCV로 비디오 파일 검증
            cap = cv2.VideoCapture(filepath)
            
            if not cap.isOpened():
                print(f"🗑️ 삭제: {filename} (OpenCV로 열 수 없음)")
                os.remove(filepath)
                deleted_count += 1
                cap.release()
                continue
            
            # 프레임 수 확인
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            # 너무 짧은 비디오들 (3초 미만)
            if duration < 3:
                print(f"🗑️ 삭제: {filename} (길이: {duration:.1f}초 - 너무 짧음)")
                os.remove(filepath)
                deleted_count += 1
                continue
            
            print(f"✅ 유지: {filename} (길이: {duration:.1f}초, 크기: {file_size:,} bytes)")
                
        except Exception as e:
            print(f"🗑️ 삭제: {filename} (오류: {e})")
            try:
                os.remove(filepath)
                deleted_count += 1
            except:
                pass
    
    print(f"\n🧹 정리 완료: {deleted_count}개 파일 삭제됨")
    
    # 남은 파일 수 확인
    remaining_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
    print(f"📁 남은 파일: {len(remaining_files)}개")

if __name__ == "__main__":
    clean_corrupted_videos()
