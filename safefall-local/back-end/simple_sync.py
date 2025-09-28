#!/usr/bin/env python3
"""
API 테스트 및 데이터베이스 동기화 스크립트
현재 상황을 진단하고 누락된 영상들을 자동 등록합니다.
"""

import requests
import json
import os
from datetime import datetime

def test_api_endpoints():
    """백엔드 API 엔드포인트들 테스트"""
    base_url = "http://localhost:5000"
    
    print("🧪 백엔드 API 테스트")
    print("=" * 50)
    
    # 1. 서버 상태 확인
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ 백엔드 서버 연결 성공")
            server_info = response.json()
            print(f"   버전: {server_info.get('version', 'Unknown')}")
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ 백엔드 서버에 연결할 수 없습니다!")
        print("   다음 명령으로 서버를 시작하세요:")
        print("   cd E:\\safefall_backend\\back-end && python app.py")
        return False
    except Exception as e:
        print(f"❌ 서버 연결 테스트 실패: {e}")
        return False
    
    # 2. 현재 영상 목록 API 테스트
    try:
        response = requests.get(f"{base_url}/api/videos/saved", timeout=10)
        print(f"\n📋 영상 목록 API (/api/videos/saved)")
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            videos = data.get('videos', [])
            print(f"   응답: {len(videos)}개 영상")
            
            if videos:
                print("   최근 영상 3개:")
                for i, video in enumerate(videos[:3], 1):
                    print(f"     {i}. {video.get('filename', 'Unknown')} (ID: {video.get('id', 'N/A')})")
            else:
                print("   ⚠️ 영상이 하나도 없습니다!")
        else:
            print(f"   ❌ 요청 실패: {response.text}")
    except Exception as e:
        print(f"   ❌ 영상 목록 API 테스트 실패: {e}")
    
    # 3. 파일시스템 영상 개수 확인
    try:
        saved_videos_dir = os.path.join(os.path.dirname(__file__), 'saved_videos')
        if os.path.exists(saved_videos_dir):
            video_files = [f for f in os.listdir(saved_videos_dir) 
                          if f.lower().endswith(('.mp4', '.avi'))]
            print(f"\n📁 파일시스템 영상: {len(video_files)}개")
            
            # 최근 파일 3개
            video_files.sort(reverse=True)
            if video_files:
                print("   최근 파일 3개:")
                for i, filename in enumerate(video_files[:3], 1):
                    print(f"     {i}. {filename}")
        else:
            print(f"\n❌ saved_videos 디렉토리가 없습니다: {saved_videos_dir}")
    except Exception as e:
        print(f"\n❌ 파일시스템 확인 실패: {e}")
    
    return True

def sync_missing_videos():
    """누락된 영상들을 데이터베이스에 동기화"""
    base_url = "http://localhost:5000"
    
    print("\n🔄 영상 동기화 시작")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{base_url}/api/videos/sync",
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"동기화 API 응답: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ 동기화 성공!")
            print(f"   전체 영상 파일: {data.get('total_videos', 0)}개")
            print(f"   DB 기존 영상: {data.get('db_videos', 0)}개")
            print(f"   누락된 영상: {data.get('missing_found', 0)}개")
            print(f"   등록 성공: {data.get('registered', 0)}개")
            print(f"   등록 실패: {data.get('failed', 0)}개")
            
            if data.get('registered', 0) > 0:
                print("\n🎉 새로운 영상이 등록되었습니다!")
                registered_videos = data.get('registered_videos', [])
                for video in registered_videos:
                    print(f"   ✅ {video.get('filename')} (ID: {video.get('event_id')})")
            else:
                print("\nℹ️ 등록할 새로운 영상이 없습니다.")
            
            if data.get('failed_videos'):
                print("\n❌ 등록 실패 영상들:")
                for video in data.get('failed_videos', []):
                    print(f"   ❌ {video.get('filename')}: {video.get('error')}")
            
            return data.get('registered', 0)
            
        else:
            print(f"❌ 동기화 실패: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   오류: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   응답: {response.text}")
            return 0
            
    except requests.exceptions.Timeout:
        print("❌ 동기화 요청 시간 초과 (30초)")
        return 0
    except Exception as e:
        print(f"❌ 동기화 중 오류: {e}")
        return 0

def main():
    """메인 함수"""
    print("🎬 SafeFall 영상 동기화 진단 도구")
    print("=" * 60)
    
    # 1. API 테스트
    if not test_api_endpoints():
        print("\n❌ 백엔드 서버가 실행되지 않았습니다.")
        print("서버를 먼저 시작한 후 다시 실행해주세요.")
        return
    
    # 2. 동기화 실행
    registered_count = sync_missing_videos()
    
    # 3. 결과 안내
    print("\n" + "=" * 60)
    print("📊 진단 완료!")
    
    if registered_count > 0:
        print(f"🎉 {registered_count}개의 새로운 영상이 등록되었습니다!")
        print("\n다음 단계:")
        print("1. 프론트엔드 페이지를 새로고침하세요")
        print("2. 영상 목록에서 새로운 영상들을 확인하세요")
    else:
        print("ℹ️ 새로 등록된 영상이 없습니다.")
        print("\n확인 사항:")
        print("1. 라즈베리파이에서 실제로 새 영상이 촬영되었는지 확인")
        print("2. saved_videos 디렉토리에 새 파일들이 있는지 확인")
        print("3. 백엔드 로그에서 영상 저장 관련 메시지 확인")
    
    print("\n🌐 프론트엔드 확인: http://localhost:5173")
    print("🔧 백엔드 API: http://localhost:5000")

if __name__ == "__main__":
    main()
