import requests
import json

def test_fall_alert():
    """낙상 감지 테스트"""
    url = "http://localhost:5000/api/test-fall-alert"
    data = {"confidence": 0.95}
    
    print(f"낙상 감지 테스트 요청: {url}")
    print(f"데이터: {data}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        
        print(f"상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("성공 응답:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("오류 응답:")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"요청 오류: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON 디코딩 오류: {e}")
        print(f"원본 응답: {response.text}")

if __name__ == "__main__":
    test_fall_alert()
