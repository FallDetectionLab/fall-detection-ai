#!/usr/bin/env python3
"""
기존 AVI 파일들을 MP4로 변환하는 스크립트
SafeFall 프로젝트용
"""

import os
import sys

# 백엔드 디렉토리를 Python 경로에 추가
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from utils.video_converter import VideoConverter

def main():
    print("🎬 SafeFall AVI → MP4 변환기")
    print("=" * 50)
    
    # saved_videos 디렉토리 경로
    saved_videos_dir = os.path.join(backend_dir, 'saved_videos')
    
    if not os.path.exists(saved_videos_dir):
        print(f"❌ saved_videos 디렉토리가 없습니다: {saved_videos_dir}")
        return
    
    print(f"📁 변환 대상 디렉토리: {saved_videos_dir}")
    
    # AVI 파일 목록 확인
    avi_files = [f for f in os.listdir(saved_videos_dir) if f.lower().endswith('.avi')]
    mp4_files = [f for f in os.listdir(saved_videos_dir) if f.lower().endswith('.mp4')]
    
    print(f"🎥 발견된 AVI 파일: {len(avi_files)}개")
    print(f"🎬 기존 MP4 파일: {len(mp4_files)}개")
    
    if not avi_files:
        print("✅ 변환할 AVI 파일이 없습니다.")
        return
    
    # 최근 3개 파일 목록 출력
    avi_files.sort(reverse=True)
    print(f"📋 최근 AVI 파일들 (최대 5개):")
    for i, file in enumerate(avi_files[:5], 1):
        file_path = os.path.join(saved_videos_dir, file)
        file_size = os.path.getsize(file_path) / (1024*1024)  # MB
        print(f"  {i}. {file} ({file_size:.1f}MB)")
    
    # 사용자 확인
    response = input(f"\n{len(avi_files)}개의 AVI 파일을 MP4로 변환하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("❌ 변환이 취소되었습니다.")
        return
    
    # 변환 시작
    print("\n🚀 변환을 시작합니다...")
    converter = VideoConverter()
    
    result = converter.convert_all_avi_in_directory(
        saved_videos_dir, 
        remove_originals=False  # 원본 파일은 보존
    )
    
    # 결과 출력
    print("\n" + "=" * 50)
    print("🎯 변환 결과:")
    print(f"  - 총 AVI 파일: {result.get('total_avi_files', 0)}개")
    print(f"  - 변환 성공: {result.get('converted', 0)}개")
    print(f"  - 변환 실패: {result.get('failed', 0)}개")
    
    if result.get('errors'):
        print("\n❌ 변환 실패 목록:")
        for error in result['errors']:
            print(f"  - {error}")
    
    # 최종 상태 확인
    mp4_files_after = [f for f in os.listdir(saved_videos_dir) if f.lower().endswith('.mp4')]
    print(f"\n📊 현재 상태:")
    print(f"  - MP4 파일: {len(mp4_files_after)}개")
    print(f"  - AVI 파일: {len(avi_files)}개")
    
    if len(mp4_files_after) > len(mp4_files):
        print(f"✅ {len(mp4_files_after) - len(mp4_files)}개의 새로운 MP4 파일이 생성되었습니다!")
        print("🌐 이제 웹 브라우저에서 영상을 재생할 수 있습니다.")
    
    print("\n🎬 변환 완료!")

if __name__ == "__main__":
    main()
