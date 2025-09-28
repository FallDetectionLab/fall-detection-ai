import requests
import json

def debug_api_data():
    """프론트엔드에서 사용하는 API 데이터 구조 확인"""
    base_url = "http://localhost:5000"
    
    print("🔍 API 데이터 구조 분석...")
    
    # 1. 저장된 비디오 목록 확인
    print("\n1. 저장된 비디오 목록 (/api/videos/saved):")
    try:
        response = requests.get(f"{base_url}/api/videos/saved")
        data = response.json()
        
        print(f"   응답 상태: {response.status_code}")
        print(f"   성공 여부: {data.get('success')}")
        print(f"   비디오 개수: {len(data.get('videos', []))}")
        
        if data.get('videos'):
            print("\n   첫 번째 비디오 샘플:")
            first_video = data['videos'][0]
            for key, value in first_video.items():
                print(f"     {key}: {value}")
                
        # filename 필드 분석
        videos = data.get('videos', [])
        filenames = []
        for video in videos:
            filename = video.get('filename') or video.get('video_filename') or video.get('name')
            filenames.append(filename)
        
        print(f"\n   파일명 분석:")
        print(f"     유효한 파일명: {len([f for f in filenames if f])}")
        print(f"     MP4 파일: {len([f for f in filenames if f and f.endswith('.mp4')])}")
        print(f"     AVI 파일: {len([f for f in filenames if f and f.endswith('.avi')])}")
        
        if filenames:
            print(f"     파일명 샘플: {filenames[:5]}")
            
    except Exception as e:
        print(f"   오류: {e}")
    
    # 2. 대시보드 최근 비디오 확인
    print("\n2. 대시보드 최근 비디오 (/api/dashboard/recent-videos):")
    try:
        response = requests.get(f"{base_url}/api/dashboard/recent-videos?limit=10")
        data = response.json()
        
        print(f"   응답 상태: {response.status_code}")
        print(f"   성공 여부: {data.get('success')}")
        print(f"   비디오 개수: {len(data.get('data', []))}")
        
        if data.get('data'):
            print("\n   첫 번째 비디오 샘플:")
            first_video = data['data'][0]
            for key, value in first_video.items():
                print(f"     {key}: {value}")
                
    except Exception as e:
        print(f"   오류: {e}")
    
    # 3. 비디오 스트림 테스트
    print("\n3. 비디오 스트림 테스트 (/video_feed):")
    try:
        response = requests.head(f"{base_url}/video_feed")
        print(f"   응답 상태: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
    except Exception as e:
        print(f"   오류: {e}")
    
    print("\n✅ API 데이터 분석 완료!")

if __name__ == "__main__":
    debug_api_data()
