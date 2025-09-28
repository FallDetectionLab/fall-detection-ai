import cv2
import numpy as np
import os

def create_web_compatible_video():
    """웹 브라우저 호환 H.264 비디오 생성"""
    output_path = os.path.join('saved_videos', 'web_test_h264.mp4')
    
    print(f"🎬 웹 호환 H.264 비디오 생성: {output_path}")
    
    # H.264 코덱 시도 (다양한 방법)
    codecs_to_try = [
        ('H264', cv2.VideoWriter_fourcc(*'H264')),
        ('avc1', cv2.VideoWriter_fourcc(*'avc1')),
        ('X264', cv2.VideoWriter_fourcc(*'X264')),
        ('mp4v', cv2.VideoWriter_fourcc(*'mp4v')),
        ('MJPG', cv2.VideoWriter_fourcc(*'MJPG')),
        ('XVID', cv2.VideoWriter_fourcc(*'XVID'))
    ]
    
    success = False
    
    for codec_name, fourcc in codecs_to_try:
        print(f"   {codec_name} 코덱 시도...")
        
        # 임시 파일명
        temp_path = output_path.replace('.mp4', f'_{codec_name.lower()}.mp4')
        
        try:
            out = cv2.VideoWriter(temp_path, fourcc, 30.0, (640, 480))
            
            if not out.isOpened():
                print(f"   ❌ {codec_name} 작성기 초기화 실패")
                continue
            
            # 짧은 테스트 비디오 생성 (30프레임 = 1초)
            for frame_num in range(30):
                # 간단한 컬러 프레임 생성
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # 컬러 그라데이션
                frame[:, :, 0] = (frame_num * 8) % 256  # Blue
                frame[:, :, 1] = (frame_num * 4) % 256  # Green  
                frame[:, :, 2] = (frame_num * 12) % 256  # Red
                
                # 텍스트 추가
                cv2.putText(frame, f"{codec_name} Test Frame {frame_num+1}", (50, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, "SafeFall Web Compatible", (50, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
                out.write(frame)
            
            out.release()
            
            # 파일이 정상적으로 생성되었는지 확인
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1000:
                file_size = os.path.getsize(temp_path)
                print(f"   ✅ {codec_name} 성공! 크기: {file_size:,} bytes")
                
                # 성공한 파일을 메인 파일로 복사
                if not success:  # 첫 번째 성공한 코덱 사용
                    os.rename(temp_path, output_path)
                    success = True
                    print(f"   🎯 {codec_name} 코덱을 메인 파일로 선택")
                else:
                    os.remove(temp_path)  # 추가 테스트 파일 삭제
            else:
                print(f"   ❌ {codec_name} 파일 생성 실패")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            print(f"   ❌ {codec_name} 오류: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    if success:
        print(f"\n✅ 웹 호환 비디오 생성 완료!")
        print(f"   파일: {output_path}")
        print(f"   테스트 URL: http://localhost:5000/media/videos/web_test_h264.mp4")
        
        # 파일 헤더 확인
        with open(output_path, 'rb') as f:
            header = f.read(20)
            print(f"   파일 헤더: {header.hex()}")
            if b'ftyp' in header:
                print(f"   ✅ 유효한 MP4 시그니처 확인")
        
        return True
    else:
        print(f"\n❌ 모든 코덱으로 비디오 생성 실패")
        return False

def test_ffmpeg_conversion():
    """FFmpeg를 사용한 웹 호환 변환 (선택사항)"""
    import subprocess
    
    input_file = os.path.join('saved_videos', 'fall_detection_20250927_114000.mp4')
    output_file = os.path.join('saved_videos', 'web_converted_h264.mp4')
    
    if not os.path.exists(input_file):
        print("❌ 변환할 원본 파일이 없습니다")
        return False
    
    try:
        print(f"🔄 FFmpeg로 웹 호환 형식 변환 시도...")
        
        # FFmpeg 명령어: H.264 + AAC로 웹 호환 변환
        cmd = [
            'ffmpeg', '-i', input_file,
            '-c:v', 'libx264',  # H.264 비디오 코덱
            '-profile:v', 'baseline',  # 웹 호환성을 위한 baseline 프로필
            '-level', '3.0',
            '-pix_fmt', 'yuv420p',  # 웹 브라우저 호환 픽셀 형식
            '-movflags', '+faststart',  # 웹 스트리밍 최적화
            '-y',  # 기존 파일 덮어쓰기
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ FFmpeg 변환 성공! 크기: {file_size:,} bytes")
            print(f"   테스트 URL: http://localhost:5000/media/videos/web_converted_h264.mp4")
            return True
        else:
            print(f"❌ FFmpeg 변환 실패: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg 변환 시간 초과")
        return False
    except FileNotFoundError:
        print("❌ FFmpeg가 설치되지 않았습니다")
        return False
    except Exception as e:
        print(f"❌ FFmpeg 변환 오류: {e}")
        return False

if __name__ == "__main__":
    print("🎬 웹 호환 비디오 생성 도구")
    print("=" * 50)
    
    # 1. OpenCV로 웹 호환 비디오 생성
    opencv_success = create_web_compatible_video()
    
    # 2. FFmpeg 변환 시도 (선택사항)
    print("\n" + "=" * 50)
    ffmpeg_success = test_ffmpeg_conversion()
    
    print("\n🎯 결과 요약:")
    print(f"   OpenCV 생성: {'✅ 성공' if opencv_success else '❌ 실패'}")
    print(f"   FFmpeg 변환: {'✅ 성공' if ffmpeg_success else '❌ 실패'}")
    
    if opencv_success or ffmpeg_success:
        print("\n🌐 브라우저에서 테스트:")
        if opencv_success:
            print("   http://localhost:5000/media/videos/web_test_h264.mp4")
        if ffmpeg_success:
            print("   http://localhost:5000/media/videos/web_converted_h264.mp4")
