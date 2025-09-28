import requests
import json

def test_api_endpoints():
    """API 엔드포인트 테스트"""
    base_url = "http://localhost:5000"
    
    print("🧪 API 엔드포인트 테스트 시작...")
    
    # 1. 영상 동기화
    print("\n1. 영상 동기화 테스트:")
    try:
        response = requests.post(f"{base_url}/api/videos/sync")
        result = response.json()
        print(f"   상태: {response.status_code}")
        print(f"   결과: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   오류: {e}")
    
    # 2. 저장된 비디오 목록
    print("\n2. 저장된 비디오 목록:")
    try:
        response = requests.get(f"{base_url}/api/videos/saved")
        result = response.json()
        print(f"   상태: {response.status_code}")
        if result.get('success') and result.get('videos'):
            print(f"   비디오 개수: {len(result['videos'])}")
            for i, video in enumerate(result['videos'][:3]):  # 처음 3개만 출력
                print(f"   비디오 {i+1}:")
                print(f"     - filename: {video.get('filename', 'UNDEFINED')}")
                print(f"     - name: {video.get('name', 'UNDEFINED')}")
                print(f"     - url: {video.get('url', 'UNDEFINED')}")
                print(f"     - path: {video.get('path', 'UNDEFINED')}")
        else:
            print(f"   결과: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   오류: {e}")
    
    # 3. 대시보드 최근 비디오
    print("\n3. 대시보드 최근 비디오:")
    try:
        response = requests.get(f"{base_url}/api/dashboard/recent-videos")
        result = response.json()
        print(f"   상태: {response.status_code}")
        if result.get('success') and result.get('data'):
            print(f"   비디오 개수: {len(result['data'])}")
            for i, video in enumerate(result['data'][:3]):
                print(f"   비디오 {i+1}:")
                print(f"     - filename: {video.get('filename', 'UNDEFINED')}")
                print(f"     - video_filename: {video.get('video_filename', 'UNDEFINED')}")
                print(f"     - url: {video.get('url', 'UNDEFINED')}")
        else:
            print(f"   결과: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   오류: {e}")
    
    # 4. 스트림 상태
    print("\n4. 스트림 상태:")
    try:
        response = requests.get(f"{base_url}/api/stream/status")
        result = response.json()
        print(f"   상태: {response.status_code}")
        print(f"   결과: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   오류: {e}")
    
    print("\n✅ API 테스트 완료!")

if __name__ == "__main__":
    test_api_endpoints()
