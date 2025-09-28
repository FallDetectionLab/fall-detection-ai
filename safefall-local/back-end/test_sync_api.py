#!/usr/bin/env python3
"""
영상 동기화 API 테스트 스크립트
"""

import requests
import json

def test_sync_api():
    """영상 동기화 API 테스트"""
    api_url = "http://localhost:5000/api/videos/sync"
    
    print("🔄 영상 동기화 API 테스트")
    print("=" * 50)
    
    try:
        print(f"📡 API 호출: {api_url}")
        response = requests.post(api_url, timeout=30)
        
        print(f"📊 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ 동기화 성공!")
            print(f"  - 전체 영상 파일: {data.get('total_videos', 0)}개")
            print(f"  - DB 기존 영상: {data.get('db_videos', 0)}개")
            print(f"  - 누락된 영상: {data.get('missing_found', 0)}개")
            print(f"  - 등록 성공: {data.get('registered', 0)}개")
            print(f"  - 등록 실패: {data.get('failed', 0)}개")
            
            if data.get('registered_videos'):
                print("\n📋 등록된 영상들:")
                for video in data['registered_videos']:
                    print(f"  ✅ {video['filename']} (ID: {video['event_id']})")
            
            if data.get('failed_videos'):
                print("\n❌ 등록 실패 영상들:")
                for video in data['failed_videos']:
                    print(f"  ❌ {video['filename']}: {video['error']}")
            
            print(f"\n💬 메시지: {data.get('message', '')}")
            
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            try:
                error_data = response.json()
                print(f"오류 내용: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"응답 내용: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ 서버 연결 실패! 백엔드 서버가 실행 중인지 확인하세요.")
        print("   실행 명령: cd E:\\safefall_backend\\back-end && python app.py")
    except requests.exceptions.Timeout:
        print("❌ 요청 시간 초과! 서버 응답이 너무 느립니다.")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

def test_videos_list():
    """영상 목록 API 테스트"""
    api_url = "http://localhost:5000/api/videos/saved"
    
    print("\n📋 영상 목록 API 테스트")
    print("=" * 50)
    
    try:
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            videos = data.get('videos', [])
            
            print(f"📊 영상 목록: {len(videos)}개")
            
            # 최근 5개 영상만 출력
            for i, video in enumerate(videos[:5], 1):
                print(f"  {i}. {video.get('filename', 'Unknown')} (ID: {video.get('id', 'N/A')})")
                print(f"     생성시간: {video.get('created_at', 'Unknown')}")
                print(f"     신뢰도: {video.get('confidence', 0):.1%}")
                print()
            
            if len(videos) > 5:
                print(f"  ... 그리고 {len(videos) - 5}개 더")
                
        else:
            print(f"❌ 영상 목록 조회 실패: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 영상 목록 조회 오류: {e}")

def main():
    """메인 함수"""
    print("🎬 SafeFall 영상 동기화 테스트")
    print("=" * 60)
    
    # 1. 동기화 API 테스트
    test_sync_api()
    
    # 2. 영상 목록 확인
    test_videos_list()
    
    print("\n✨ 테스트 완료!")
    print("🌐 프론트엔드에서 영상 목록을 새로고침해보세요!")

if __name__ == "__main__":
    main()
