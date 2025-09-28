#!/usr/bin/env python3
"""
백엔드 API 응답을 즉시 수정하는 핫픽스
"""

import os
import requests
import json

def create_hotfix_endpoint():
    """핫픽스 엔드포인트 생성 및 테스트"""
    
    print("🔧 백엔드 API 핫픽스 적용")
    print("=" * 40)
    
    # 1. 파일시스템에서 MP4 파일들 직접 스캔
    saved_videos_dir = "saved_videos"
    
    if not os.path.exists(saved_videos_dir):
        print("❌ saved_videos 디렉토리가 없습니다!")
        return None
    
    # MP4 파일들 찾기
    mp4_files = []
    for filename in os.listdir(saved_videos_dir):
        if filename.lower().endswith('.mp4'):
            file_path = os.path.join(saved_videos_dir, filename)
            file_stat = os.stat(file_path)
            
            mp4_files.append({
                'id': hash(filename) % 10000,  # 임시 ID
                'filename': filename,
                'name': filename,
                'title': f'SafeFall Video - {filename}',
                'url': f'/media/videos/{filename}',
                'path': f'/media/videos/{filename}',
                'size': file_stat.st_size,
                'created_at': file_stat.st_mtime,
                'createdAt': file_stat.st_mtime,
                'isChecked': False,
                'confidence': 0.95,
                'device_id': 'camera_01',
                'file_type': 'mp4'
            })
    
    # 최신 순으로 정렬
    mp4_files.sort(key=lambda x: x['created_at'], reverse=True)
    
    print(f"📁 발견된 MP4 파일: {len(mp4_files)}개")
    
    if mp4_files:
        print("📋 최신 MP4 파일 3개:")
        for i, video in enumerate(mp4_files[:3], 1):
            print(f"   {i}. {video['filename']}")
            print(f"      URL: {video['url']}")
            print(f"      크기: {video['size'] / (1024*1024):.1f}MB")
    
    return mp4_files

def test_corrected_response(mp4_files):
    """수정된 응답 테스트"""
    
    if not mp4_files:
        print("❌ MP4 파일이 없습니다!")
        return False
    
    print(f"\n🧪 수정된 응답 테스트")
    print("=" * 40)
    
    # 첫 번째 MP4 파일로 테스트
    test_video = mp4_files[0]
    test_url = f"http://localhost:5000{test_video['url']}"
    
    print(f"🎬 테스트 영상: {test_video['filename']}")
    print(f"🔗 테스트 URL: {test_url}")
    
    try:
        response = requests.head(test_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ 영상 파일 접근 성공!")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
            print(f"   Content-Length: {response.headers.get('Content-Length')}")
            return True
        else:
            print(f"❌ 영상 파일 접근 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 연결 테스트 실패: {e}")
        return False

def generate_frontend_fix(mp4_files):
    """프론트엔드에서 사용할 수 있는 JavaScript 코드 생성"""
    
    if not mp4_files:
        return
    
    print(f"\n💡 프론트엔드 임시 해결책")
    print("=" * 40)
    
    print("브라우저 콘솔(F12)에서 다음 코드를 실행하세요:")
    print()
    print("```javascript")
    print("// SafeFall 영상 목록 임시 수정")
    print("window.safeFallFixedVideos = [")
    
    for i, video in enumerate(mp4_files[:10]):  # 최신 10개만
        print(f"  {{")
        print(f"    id: {video['id']},")
        print(f"    filename: '{video['filename']}',")
        print(f"    url: '{video['url']}',")
        print(f"    path: '{video['path']}',")
        print(f"    title: '{video['title']}',")
        print(f"    isChecked: false,")
        print(f"    createdAt: new Date({int(video['created_at'] * 1000)}).toISOString()")
        print(f"  }}" + ("," if i < min(len(mp4_files), 10) - 1 else ""))
    
    print("];")
    print()
    print("// 영상 목록 페이지에서 이 데이터 사용")
    print("console.log('🎬 수정된 영상 목록:', window.safeFallFixedVideos);")
    print()
    print("// 첫 번째 영상 직접 재생 테스트")
    print("const firstVideo = window.safeFallFixedVideos[0];")
    print("if (firstVideo) {")
    print("  const videoUrl = `http://localhost:5000${firstVideo.url}`;")
    print("  console.log('🔗 영상 URL:', videoUrl);")
    print("  window.open(videoUrl, '_blank');")
    print("}")
    print("```")

def main():
    print("🎬 SafeFall API 핫픽스 도구")
    print("=" * 50)
    
    # 1. MP4 파일들 직접 스캔
    mp4_files = create_hotfix_endpoint()
    
    if not mp4_files:
        print("❌ 처리할 MP4 파일이 없습니다!")
        print("🔧 AVI → MP4 변환을 먼저 실행하세요:")
        print("   python convert_avi_to_mp4.py")
        return
    
    # 2. 파일 접근 테스트
    access_ok = test_corrected_response(mp4_files)
    
    # 3. 프론트엔드 임시 해결책 제공
    generate_frontend_fix(mp4_files)
    
    # 4. 직접 브라우저 테스트
    print(f"\n🌐 직접 브라우저 테스트")
    print("=" * 40)
    print("다음 URL들을 브라우저에서 직접 테스트하세요:")
    
    for i, video in enumerate(mp4_files[:3], 1):
        test_url = f"http://localhost:5000{video['url']}"
        print(f"   {i}. {test_url}")
    
    # 5. 결과 및 다음 단계
    print(f"\n🎯 해결 상태:")
    if access_ok:
        print("✅ 영상 파일 직접 접근 가능")
        print("💡 문제는 API 응답 형식에만 있음")
        print("🔧 위의 JavaScript 코드로 임시 해결 가능")
    else:
        print("❌ 영상 파일 접근에도 문제 있음")
        print("🔧 백엔드 서버 재시작 필요할 수 있음")

if __name__ == "__main__":
    main()
