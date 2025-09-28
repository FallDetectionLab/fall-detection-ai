import os
import subprocess

def check_video_integrity():
    """비디오 파일 무결성 및 형식 확인"""
    video_dir = os.path.abspath('saved_videos')
    test_file = 'fall_detection_20250927_114000.mp4'
    file_path = os.path.join(video_dir, test_file)
    
    print(f"🎬 비디오 파일 무결성 검사: {test_file}")
    print(f"📁 파일 경로: {file_path}")
    
    if not os.path.exists(file_path):
        print("❌ 파일이 존재하지 않습니다!")
        return
    
    # 파일 기본 정보
    file_size = os.path.getsize(file_path)
    print(f"📊 파일 크기: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # 파일 헤더 확인 (첫 16바이트)
    with open(file_path, 'rb') as f:
        header = f.read(16)
        print(f"🔍 파일 헤더: {header.hex()}")
        
        # MP4 시그니처 확인
        if b'ftyp' in header:
            print("✅ 유효한 MP4 파일 시그니처 발견")
        else:
            print("❌ MP4 파일 시그니처가 없습니다")
    
    # ffprobe로 상세 정보 확인 (있는 경우)
    try:
        print("\n🔍 FFprobe로 상세 분석:")
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_format', '-show_streams', file_path
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            # 형식 정보
            if 'format' in data:
                fmt = data['format']
                print(f"   형식: {fmt.get('format_name', 'Unknown')}")
                print(f"   지속시간: {fmt.get('duration', 'Unknown')}초")
                print(f"   비트레이트: {fmt.get('bit_rate', 'Unknown')}")
            
            # 스트림 정보
            if 'streams' in data:
                for i, stream in enumerate(data['streams']):
                    print(f"   스트림 {i}: {stream.get('codec_name', 'Unknown')} ({stream.get('codec_type', 'Unknown')})")
                    if stream.get('codec_type') == 'video':
                        print(f"     해상도: {stream.get('width')}x{stream.get('height')}")
                        print(f"     프레임율: {stream.get('r_frame_rate')}")
        else:
            print("   FFprobe 분석 실패 또는 설치되지 않음")
            
    except Exception as e:
        print(f"   FFprobe 오류: {e}")
    
    # 웹 호환성 확인
    print("\n🌐 웹 브라우저 호환성 확인:")
    web_compatible_codecs = ['h264', 'avc1']
    
    try:
        # 간단한 코덱 확인
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-select_streams', 'v:0', 
            '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', file_path
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            codec = result.stdout.strip()
            print(f"   비디오 코덱: {codec}")
            if codec.lower() in web_compatible_codecs:
                print("   ✅ 웹 브라우저 호환 코덱")
            else:
                print("   ❌ 웹 브라우저 비호환 코덱 (변환 필요)")
        else:
            print("   코덱 정보 확인 실패")
            
    except Exception as e:
        print(f"   코덱 확인 오류: {e}")
    
    # 다른 파일들도 간단히 확인
    print(f"\n📋 다른 비디오 파일들 확인:")
    video_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')][:5]
    
    for video_file in video_files:
        vf_path = os.path.join(video_dir, video_file)
        vf_size = os.path.getsize(vf_path)
        
        with open(vf_path, 'rb') as f:
            vf_header = f.read(8)
            has_ftyp = b'ftyp' in vf_header
            
        print(f"   {video_file}: {vf_size:,} bytes, MP4시그니처: {'✅' if has_ftyp else '❌'}")

if __name__ == "__main__":
    check_video_integrity()
