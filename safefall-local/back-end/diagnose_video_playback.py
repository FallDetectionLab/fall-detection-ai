#!/usr/bin/env python3
"""
영상 재생 문제 진단 스크립트
"""

import requests
import json
import os

def check_video_files():
    """저장된 영상 파일들 상태 확인"""
    print("📁 영상 파일 상태 확인")
    print("=" * 40)
    
    saved_videos_dir = "saved_videos"
    
    if not os.path.exists(saved_videos_dir):
        print(f"❌ {saved_videos_dir} 디렉토리가 없습니다!")
        return
    
    # 파일 목록
    all_files = os.listdir(saved_videos_dir)
    video_files = [f for f in all_files if f.lower().endswith(('.mp4', '.avi'))]
    
    mp4_files = [f for f in video_files if f.lower().endswith('.mp4')]
    avi_files = [f for f in video_files if f.lower().endswith('.avi')]
    
    print(f"📊 전체 영상 파일: {len(video_files)}개")
    print(f"   - MP4 파일: {len(mp4_files)}개 (웹 호환)")
    print(f"   - AVI 파일: {len(avi_files)}개 (변환 필요)")
    
    # 최근 파일들 상세 정보
    video_files.sort(reverse=True)
    print(f"\n📋 최근 영상 5개:")
    for i, filename in enumerate(video_files[:5], 1):
        file_path = os.path.join(saved_videos_dir, filename)
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        file_type = "🎬 MP4 (재생가능)" if filename.endswith('.mp4') else "⚠️ AVI (변환필요)"
        print(f"   {i}. {filename}")
        print(f"      {file_type} - {file_size:.1f}MB")

def test_video_api():
    """영상 API 응답 확인"""
    print(f"\n🌐 영상 API 응답 확인")
    print("=" * 40)
    
    try:
        response = requests.get("http://localhost:5000/api/videos/saved", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            videos = data.get('videos', [])
            
            print(f"✅ API 응답: {len(videos)}개 영상")
            
            if videos:
                print(f"\n📋 API에서 반환하는 최근 영상 3개:")
                for i, video in enumerate(videos[:3], 1):
                    print(f"   {i}. 파일명: {video.get('filename', 'Unknown')}")
                    print(f"      ID: {video.get('id', 'N/A')}")
                    print(f"      URL: {video.get('url', 'No URL')}")
                    print(f"      경로: {video.get('path', 'No Path')}")
                    print(f"      파일타입: {video.get('file_type', 'Unknown')}")
                    print()
        else:
            print(f"❌ API 오류: {response.status_code}")
            print(f"   응답: {response.text}")
            
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")

def test_video_serving():
    """실제 영상 서빙 테스트"""
    print(f"🎬 영상 서빙 테스트")
    print("=" * 40)
    
    # 파일시스템에서 최근 파일 찾기
    saved_videos_dir = "saved_videos"
    
    if os.path.exists(saved_videos_dir):
        video_files = [f for f in os.listdir(saved_videos_dir) 
                      if f.lower().endswith(('.mp4', '.avi'))]
        video_files.sort(reverse=True)
        
        if video_files:
            # 최신 MP4 파일 우선 테스트
            mp4_files = [f for f in video_files if f.lower().endswith('.mp4')]
            test_file = mp4_files[0] if mp4_files else video_files[0]
            
            print(f"🧪 테스트 파일: {test_file}")
            
            # 직접 파일 서빙 테스트
            test_url = f"http://localhost:5000/media/videos/{test_file}"
            
            try:
                response = requests.head(test_url, timeout=10)
                print(f"📡 서빙 테스트: {test_url}")
                print(f"   상태 코드: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
                print(f"   Content-Length: {response.headers.get('Content-Length', 'Unknown')}")
                
                if response.status_code == 200:
                    print(f"   ✅ 파일 서빙 성공!")
                    print(f"   🌐 브라우저 테스트: {test_url}")
                else:
                    print(f"   ❌ 서빙 실패: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ 서빙 테스트 오류: {e}")
        else:
            print("❌ 테스트할 영상 파일이 없습니다!")

def suggest_solutions():
    """해결책 제안"""
    print(f"\n💡 해결책 제안")
    print("=" * 40)
    
    print("🔧 영상 재생 문제 해결 방법:")
    print()
    print("1️⃣ AVI 파일 문제인 경우:")
    print("   - AVI 파일은 웹 브라우저에서 재생되지 않음")
    print("   - MP4로 변환 필요")
    print("   - 명령: python convert_avi_to_mp4.py")
    print()
    print("2️⃣ 파일 경로 문제인 경우:")
    print("   - 백엔드에서 올바른 URL 반환하는지 확인")
    print("   - /media/videos/ 경로 작동 확인")
    print()
    print("3️⃣ 브라우저 테스트:")
    print("   - 직접 URL 접속: http://localhost:5000/media/videos/[파일명]")
    print("   - 개발자 도구에서 네트워크 탭 확인")
    print()
    print("4️⃣ 서버 로그 확인:")
    print("   - 백엔드 터미널에서 오류 메시지 확인")

def main():
    print("🎬 SafeFall 영상 재생 문제 진단")
    print("=" * 50)
    
    check_video_files()
    test_video_api()
    test_video_serving()
    suggest_solutions()

if __name__ == "__main__":
    main()
