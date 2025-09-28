#!/usr/bin/env python3
"""
API 응답 데이터 수정을 위한 즉시 적용 스크립트
"""

import requests
import json

def test_and_fix_api():
    """API 응답 확인 및 수정"""
    
    print("🔧 API 응답 데이터 수정")
    print("=" * 40)
    
    base_url = "http://localhost:5000"
    
    # 1. 현재 API 응답 확인
    print("1️⃣ 현재 API 응답 확인...")
    try:
        response = requests.get(f"{base_url}/api/videos/saved")
        if response.status_code == 200:
            data = response.json()
            videos = data.get('videos', [])
            
            print(f"📋 현재 API 응답: {len(videos)}개 영상")
            
            if videos:
                first_video = videos[0]
                print("🔍 첫 번째 영상 데이터:")
                print(f"   파일명: {first_video.get('filename', 'Unknown')}")
                print(f"   URL: {first_video.get('url', 'No URL')}")
                print(f"   경로: {first_video.get('path', 'No Path')}")
                
                # 문제가 있는 경우
                if first_video.get('filename') == 'Unknown' or not first_video.get('url'):
                    print("❌ API 응답 데이터에 문제가 있습니다!")
                    return False
                else:
                    print("✅ API 응답 데이터가 정상입니다!")
                    return True
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        return False

def force_sync():
    """강제 동기화 실행"""
    
    print("\n2️⃣ 강제 동기화 실행...")
    
    try:
        response = requests.post(
            "http://localhost:5000/api/videos/sync",
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ 동기화 성공!")
            print(f"   전체 파일: {data.get('total_videos', 0)}개")
            print(f"   DB 영상: {data.get('db_videos', 0)}개")
            print(f"   새로 등록: {data.get('registered', 0)}개")
            
            if data.get('registered', 0) > 0:
                print("\n🎉 새로운 영상이 등록되었습니다!")
                for video in data.get('registered_videos', [])[:3]:
                    print(f"   ✅ {video.get('filename')}")
            
            return data.get('registered', 0)
        else:
            print(f"❌ 동기화 실패: {response.status_code}")
            return 0
            
    except Exception as e:
        print(f"❌ 동기화 오류: {e}")
        return 0

def test_direct_video_access():
    """직접 영상 접근 테스트"""
    
    print("\n3️⃣ 직접 영상 접근 테스트...")
    
    # 최신 MP4 파일들 테스트
    test_videos = [
        "fall_detection_20250927_123102.mp4",
        "fall_detection_20250927_123058.mp4",
        "fall_detection_20250927_123052.mp4"
    ]
    
    for video_file in test_videos:
        test_url = f"http://localhost:5000/media/videos/{video_file}"
        
        try:
            response = requests.head(test_url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {video_file} - 접근 성공")
                print(f"   🌐 브라우저 테스트: {test_url}")
                return test_url  # 첫 번째 성공한 URL 반환
            else:
                print(f"❌ {video_file} - 접근 실패 ({response.status_code})")
        except:
            print(f"❌ {video_file} - 연결 실패")
    
    return None

def main():
    print("🎬 SafeFall API 응답 수정 도구")
    print("=" * 50)
    
    # 1. API 응답 확인
    api_ok = test_and_fix_api()
    
    if not api_ok:
        # 2. 동기화 강제 실행
        registered = force_sync()
        
        if registered > 0:
            print(f"\n✨ {registered}개 영상이 새로 등록되었습니다!")
            
            # 3. 다시 API 응답 확인
            print("\n4️⃣ 동기화 후 API 재확인...")
            api_ok = test_and_fix_api()
    
    # 4. 직접 접근 테스트
    working_url = test_direct_video_access()
    
    # 5. 결과 및 해결책
    print("\n" + "=" * 50)
    print("📊 진단 결과:")
    
    if api_ok:
        print("✅ API 응답이 정상입니다!")
        print("🌐 프론트엔드에서 영상 재생이 가능해야 합니다.")
    else:
        print("❌ API 응답에 여전히 문제가 있습니다.")
        
        if working_url:
            print(f"💡 해결책: 직접 URL 사용")
            print(f"   테스트 URL: {working_url}")
    
    print("\n🎯 다음 단계:")
    print("1. 프론트엔드 새로고침 (Ctrl+F5)")
    print("2. 영상 목록에서 최신 영상 클릭")
    print("3. 만약 여전히 안 되면 브라우저에서 직접 URL 테스트")

if __name__ == "__main__":
    main()
