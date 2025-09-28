#!/usr/bin/env python3
"""
SafeFall 시스템 진단 스크립트
- 백엔드 서버 상태 확인
- 데이터베이스 vs 파일시스템 비교
- API 테스트
"""

import requests
import sqlite3
import os
from datetime import datetime

def test_backend_server():
    """백엔드 서버 연결 테스트"""
    print("🌐 백엔드 서버 연결 테스트")
    print("-" * 40)
    
    try:
        # 기본 엔드포인트 테스트
        response = requests.get("http://localhost:5000", timeout=5)
        print(f"✅ 서버 상태: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   버전: {data.get('version', 'Unknown')}")
            print(f"   상태: {data.get('status', 'Unknown')}")
            print(f"   서비스 로드: {data.get('services_loaded', 'Unknown')}")
        
        return True
    except requests.exceptions.ConnectionError:
        print("❌ 서버 연결 실패!")
        print("   → 백엔드 서버가 실행되지 않았습니다.")
        return False
    except Exception as e:
        print(f"❌ 서버 테스트 오류: {e}")
        return False

def check_database_status():
    """데이터베이스 상태 확인"""
    print("\\n💾 데이터베이스 상태 확인")
    print("-" * 40)
    
    db_path = "safefall.db"
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return 0
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fall_events';")
        if not cursor.fetchone():
            print("❌ fall_events 테이블이 없습니다!")
            conn.close()
            return 0
        
        # 데이터 개수 확인
        cursor.execute("SELECT COUNT(*) FROM fall_events")
        total_events = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fall_events WHERE video_filename IS NOT NULL")
        video_events = cursor.fetchone()[0]
        
        print(f"📊 총 이벤트: {total_events}개")
        print(f"🎬 비디오 연결 이벤트: {video_events}개")
        
        # 최근 5개 이벤트
        cursor.execute("""
            SELECT id, video_filename, created_at 
            FROM fall_events 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent_events = cursor.fetchall()
        
        if recent_events:
            print("\\n📋 최근 5개 이벤트:")
            for event in recent_events:
                filename = event[1] or "NO_VIDEO"
                print(f"   ID:{event[0]} {filename}")
        
        conn.close()
        return video_events
        
    except Exception as e:
        print(f"❌ 데이터베이스 오류: {e}")
        return 0

def check_filesystem_status():
    """파일시스템 상태 확인"""
    print("\\n📁 파일시스템 상태 확인")
    print("-" * 40)
    
    video_dir = "saved_videos"
    if not os.path.exists(video_dir):
        print(f"❌ {video_dir} 디렉토리가 없습니다!")
        return 0, []
    
    # 영상 파일 목록
    video_files = []
    for filename in os.listdir(video_dir):
        if filename.lower().endswith(('.mp4', '.avi')):
            file_path = os.path.join(video_dir, filename)
            stat = os.stat(file_path)
            video_files.append({
                'filename': filename,
                'size': stat.st_size,
                'mtime': datetime.fromtimestamp(stat.st_mtime)
            })
    
    video_files.sort(key=lambda x: x['mtime'], reverse=True)
    
    # 파일 타입별 분류
    mp4_files = [f for f in video_files if f['filename'].endswith('.mp4')]
    avi_files = [f for f in video_files if f['filename'].endswith('.avi')]
    
    print(f"📊 총 영상 파일: {len(video_files)}개")
    print(f"   - MP4: {len(mp4_files)}개")
    print(f"   - AVI: {len(avi_files)}개")
    
    if video_files:
        print("\\n📋 최근 5개 파일:")
        for i, video in enumerate(video_files[:5], 1):
            size_mb = video['size'] / (1024 * 1024)
            print(f"   {i}. {video['filename']} ({size_mb:.1f}MB)")
    
    return len(video_files), [f['filename'] for f in video_files]

def test_sync_api():
    """동기화 API 테스트"""
    print("\\n🔄 동기화 API 테스트")
    print("-" * 40)
    
    try:
        response = requests.post("http://localhost:5000/api/videos/sync", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 동기화 API 정상 작동")
            print(f"   - 전체 파일: {data.get('total_videos', 0)}개")
            print(f"   - DB 기존: {data.get('db_videos', 0)}개")
            print(f"   - 누락 발견: {data.get('missing_found', 0)}개")
            print(f"   - 등록 성공: {data.get('registered', 0)}개")
            print(f"   - 등록 실패: {data.get('failed', 0)}개")
            
            if data.get('registered', 0) > 0:
                print(f"\\n🎉 {data['registered']}개 영상이 새로 등록되었습니다!")
            
            return data.get('registered', 0)
        else:
            print(f"❌ 동기화 API 오류: {response.status_code}")
            print(f"   응답: {response.text[:200]}")
            return 0
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버 연결 실패! 백엔드가 실행 중인지 확인하세요.")
        return 0
    except Exception as e:
        print(f"❌ 동기화 API 오류: {e}")
        return 0

def test_videos_api():
    """영상 목록 API 테스트"""
    print("\\n📋 영상 목록 API 테스트")
    print("-" * 40)
    
    try:
        response = requests.get("http://localhost:5000/api/videos/saved", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            videos = data.get('videos', [])
            print(f"✅ 영상 목록 API 정상 작동")
            print(f"   - 반환된 영상: {len(videos)}개")
            
            if videos:
                print("\\n📋 최근 3개 영상:")
                for i, video in enumerate(videos[:3], 1):
                    print(f"   {i}. {video.get('filename', 'NO_NAME')} (ID: {video.get('id', 'NO_ID')})")
            
            return len(videos)
        else:
            print(f"❌ 영상 목록 API 오류: {response.status_code}")
            return 0
            
    except Exception as e:
        print(f"❌ 영상 목록 API 오류: {e}")
        return 0

def main():
    """메인 진단 함수"""
    print("🔍 SafeFall 시스템 종합 진단")
    print("=" * 50)
    
    # 1. 백엔드 서버 테스트
    server_ok = test_backend_server()
    
    if not server_ok:
        print("\\n🚨 백엔드 서버가 실행되지 않았습니다!")
        print("   실행 명령: cd E:\\\\safefall_backend\\\\back-end && python app.py")
        return
    
    # 2. 데이터베이스 상태
    db_videos = check_database_status()
    
    # 3. 파일시스템 상태
    fs_videos, fs_filenames = check_filesystem_status()
    
    # 4. 동기화 필요성 판단
    print(f"\\n📊 동기화 필요성 분석")
    print("-" * 40)
    missing_count = fs_videos - db_videos
    print(f"파일시스템 영상: {fs_videos}개")
    print(f"데이터베이스 영상: {db_videos}개")
    print(f"누락 추정: {missing_count}개")
    
    if missing_count > 0:
        print("\\n⚠️  동기화가 필요합니다!")
        
        # 5. 동기화 API 테스트
        registered = test_sync_api()
        
        if registered > 0:
            # 6. 동기화 후 영상 목록 API 테스트
            api_videos = test_videos_api()
            
            print(f"\\n🎯 결과 요약")
            print("-" * 40)
            print(f"✅ {registered}개 영상이 데이터베이스에 등록되었습니다!")
            print(f"📋 API가 반환하는 영상: {api_videos}개")
            print("🌐 이제 프론트엔드에서 영상을 확인할 수 있습니다!")
            
        else:
            print("\\n❌ 동기화에 실패했습니다.")
    else:
        print("\\n✅ 동기화가 필요하지 않습니다.")
        
        # 영상 목록 API만 테스트
        api_videos = test_videos_api()
        print(f"\\n📋 API가 반환하는 영상: {api_videos}개")
    
    print("\\n🏁 진단 완료!")

if __name__ == "__main__":
    main()
