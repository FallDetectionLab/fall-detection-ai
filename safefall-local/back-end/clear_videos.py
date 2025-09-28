#!/usr/bin/env python3
"""모든 비디오 파일 삭제"""
import os
import shutil

def clear_all_videos():
    video_dir = "saved_videos"
    
    if os.path.exists(video_dir):
        # 디렉토리 내 모든 파일 삭제
        for filename in os.listdir(video_dir):
            filepath = os.path.join(video_dir, filename)
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    print(f"삭제: {filename}")
            except Exception as e:
                print(f"삭제 실패: {filename} - {e}")
        
        print(f"모든 비디오 파일 삭제 완료")
    else:
        print("saved_videos 디렉토리가 없습니다")

if __name__ == "__main__":
    clear_all_videos()
