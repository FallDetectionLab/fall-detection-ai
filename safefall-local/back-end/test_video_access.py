import requests

def test_video_access():
    """비디오 파일 직접 접근 테스트"""
    base_url = "http://localhost:5000"
    test_filename = "fall_detection_20250927_114000.mp4"
    
    print(f"🧪 비디오 파일 접근 테스트: {test_filename}")
    
    # 1. HEAD 요청으로 파일 존재 확인
    print("\n1. HEAD 요청 테스트:")
    try:
        response = requests.head(f"{base_url}/media/videos/{test_filename}")
        print(f"   상태 코드: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   Content-Length: {response.headers.get('Content-Length')}")
        print(f"   CORS 헤더: {response.headers.get('Access-Control-Allow-Origin')}")
    except Exception as e:
        print(f"   오류: {e}")
    
    # 2. GET 요청으로 실제 데이터 확인
    print("\n2. GET 요청 테스트 (처음 1024바이트만):")
    try:
        response = requests.get(f"{base_url}/media/videos/{test_filename}", 
                              stream=True, 
                              headers={'Range': 'bytes=0-1023'})
        print(f"   상태 코드: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   받은 데이터 크기: {len(response.content)} bytes")
        print(f"   CORS 헤더: {response.headers.get('Access-Control-Allow-Origin')}")
        
        if response.content:
            print(f"   데이터 시작: {response.content[:20].hex()}")
    except Exception as e:
        print(f"   오류: {e}")
    
    # 3. 대체 파일명들도 테스트
    print("\n3. 다른 파일명들 테스트:")
    alternative_files = [
        "fall_detection_20250927_114000.avi",
        "fall_detection_20250927_122047.mp4",
        "fall_detection_20250927_144723.mp4"
    ]
    
    for alt_file in alternative_files:
        try:
            response = requests.head(f"{base_url}/media/videos/{alt_file}")
            print(f"   {alt_file}: {response.status_code}")
        except Exception as e:
            print(f"   {alt_file}: 오류 - {e}")

if __name__ == "__main__":
    test_video_access()
