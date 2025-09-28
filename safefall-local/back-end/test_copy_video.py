#!/usr/bin/env python3
"""
정상적인 테스트 비디오 파일을 생성하는 스크립트
"""

import os
import shutil
from datetime import datetime

def create_test_video():
    saved_videos_dir = "saved_videos"
    
    # 임시 테스트용 작은 비디오 생성 (실제로는 외부 파일을 복사하는 것이 좋음)
    test_filename = f"test_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    test_path = os.path.join(saved_videos_dir, test_filename)
    
    print(f"테스트 비디오 파일명: {test_filename}")
    print(f"경로: {test_path}")
    
    # 실제로는 정상적인 MP4 파일을 복사해야 합니다
    # 예: shutil.copy("path/to/normal/video.mp4", test_path)
    print("정상적인 MP4 파일을 이 경로로 복사해주세요.")
    
    return test_filename

if __name__ == "__main__":
    create_test_video()
