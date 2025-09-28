import requests

def test_from_react_port():
    """React 앱 포트에서 비디오 접근 테스트"""
    base_url = "http://localhost:5000"
    test_filename = "fall_detection_20250927_114000.mp4"
    
    # React 앱에서 보내는 것과 동일한 헤더로 테스트
    react_headers = {
        'Origin': 'http://localhost:5173',  # Vite 기본 포트
        'Referer': 'http://localhost:5173/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"🎯 React 앱 시뮬레이션 테스트: {test_filename}")
    print(f"Origin: {react_headers['Origin']}")
    
    # 1. OPTIONS 요청 테스트 (preflight)
    print("\n1. OPTIONS 요청 (CORS preflight):")
    try:
        response = requests.options(f"{base_url}/media/videos/{test_filename}", 
                                  headers=react_headers)
        print(f"   상태 코드: {response.status_code}")
        print(f"   Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
        print(f"   Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods')}")
        print(f"   Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers')}")
    except Exception as e:
        print(f"   오류: {e}")
    
    # 2. GET 요청 테스트
    print("\n2. GET 요청 (React 시뮬레이션):")
    try:
        response = requests.get(f"{base_url}/media/videos/{test_filename}", 
                              headers=react_headers,
                              stream=True)
        print(f"   상태 코드: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
        print(f"   받은 데이터 크기: {len(response.content)} bytes")
    except Exception as e:
        print(f"   오류: {e}")
    
    # 3. 다른 포트들도 테스트
    print("\n3. 다른 React 포트들 테스트:")
    test_origins = [
        'http://localhost:3000',  # Create React App
        'http://localhost:5173',  # Vite
        'http://127.0.0.1:5173',  # Vite 로컬호스트
    ]
    
    for origin in test_origins:
        try:
            headers = {'Origin': origin}
            response = requests.head(f"{base_url}/media/videos/{test_filename}", 
                                   headers=headers)
            cors_header = response.headers.get('Access-Control-Allow-Origin', 'None')
            print(f"   {origin}: {response.status_code} (CORS: {cors_header})")
        except Exception as e:
            print(f"   {origin}: 오류 - {e}")

if __name__ == "__main__":
    test_from_react_port()
