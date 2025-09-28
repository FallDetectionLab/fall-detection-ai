import subprocess
import os

def fix_mp4_for_web():
    """FFmpeg가 있다면 웹 스트리밍 최적화"""
    video_dir = 'saved_videos'
    
    # 테스트할 파일들
    source_files = [
        'web_test_h264.mp4',
        'simple_web_test.mp4', 
        'minimal_web.mp4',
        'web_reliable_mp4v.mp4'
    ]
    
    print("🔧 MP4 파일 웹 스트리밍 최적화 (FFmpeg 필요)")
    
    for source_file in source_files:
        source_path = os.path.join(video_dir, source_file)
        if not os.path.exists(source_path):
            print(f"⏭️ {source_file} - 파일 없음")
            continue
            
        output_file = f"webstream_{source_file}"
        output_path = os.path.join(video_dir, output_file)
        
        print(f"🔄 {source_file} → {output_file}")
        
        try:
            # FFmpeg로 웹 스트리밍 최적화
            cmd = [
                'ffmpeg', '-i', source_path,
                '-c:v', 'libx264',          # H.264 비디오 코덱
                '-profile:v', 'baseline',    # 웹 호환성 프로필
                '-level', '3.0',
                '-pix_fmt', 'yuv420p',      # 픽셀 형식
                '-movflags', '+faststart',   # 웹 스트리밍 최적화 (moov atom을 앞으로)
                '-crf', '23',               # 품질 설정
                '-y',                       # 덮어쓰기
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"   ✅ 성공! 크기: {file_size:,} bytes")
                print(f"   🌐 URL: http://localhost:5000/media/videos/{output_file}")
            else:
                print(f"   ❌ 실패: {result.stderr[:100]}...")
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ 시간 초과")
        except FileNotFoundError:
            print(f"   ❌ FFmpeg가 설치되지 않았습니다")
            break
        except Exception as e:
            print(f"   ❌ 오류: {e}")

if __name__ == "__main__":
    fix_mp4_for_web()
