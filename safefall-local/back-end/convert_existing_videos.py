import cv2
import os
import numpy as np

def convert_videos_to_web_compatible():
    """기존 비디오들을 웹 호환 형식으로 변환"""
    video_dir = 'saved_videos'
    
    print("🔄 기존 비디오 파일들을 웹 호환 형식으로 변환 중...")
    
    # 모든 비디오 파일 찾기
    video_files = []
    for filename in os.listdir(video_dir):
        if filename.lower().endswith(('.mp4', '.avi')) and not filename.startswith('web_'):
            video_files.append(filename)
    
    print(f"📋 변환할 파일 수: {len(video_files)}")
    
    converted_count = 0
    failed_count = 0
    
    for filename in video_files:
        input_path = os.path.join(video_dir, filename)
        
        # 출력 파일명 생성 (web_ 접두사 추가)
        name_without_ext = os.path.splitext(filename)[0]
        output_filename = f"web_{name_without_ext}.mp4"
        output_path = os.path.join(video_dir, output_filename)
        
        # 이미 변환된 파일이 있으면 건너뛰기
        if os.path.exists(output_path):
            print(f"   ⏭️ {filename} - 이미 변환됨")
            continue
        
        print(f"   🔄 {filename} 변환 중...")
        
        try:
            # 입력 비디오 열기
            cap = cv2.VideoCapture(input_path)
            
            if not cap.isOpened():
                print(f"   ❌ {filename} - 입력 파일을 열 수 없음")
                failed_count += 1
                continue
            
            # 원본 비디오 정보 가져오기
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            print(f"     원본: {width}x{height}, {fps:.1f}fps, {total_frames}프레임")
            
            # 웹 호환 출력 설정 (mp4v 코덱 사용 - 가장 호환성이 좋음)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                print(f"   ❌ {filename} - 출력 파일을 생성할 수 없음")
                cap.release()
                failed_count += 1
                continue
            
            # 프레임별 변환
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                out.write(frame)
                frame_count += 1
                
                # 진행 상황 표시 (10% 단위)
                if frame_count % max(1, total_frames // 10) == 0:
                    progress = (frame_count / total_frames) * 100
                    print(f"     진행: {progress:.0f}%")
            
            cap.release()
            out.release()
            
            # 변환 결과 확인
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                output_size = os.path.getsize(output_path)
                print(f"   ✅ {filename} 변환 완료! 크기: {output_size:,} bytes")
                converted_count += 1
            else:
                print(f"   ❌ {filename} 변환 실패")
                if os.path.exists(output_path):
                    os.remove(output_path)
                failed_count += 1
                
        except Exception as e:
            print(f"   ❌ {filename} 변환 오류: {e}")
            failed_count += 1
    
    print(f"\n🎯 변환 완료!")
    print(f"   성공: {converted_count}개")
    print(f"   실패: {failed_count}개")
    
    # 변환된 파일들 목록 표시
    if converted_count > 0:
        print(f"\n📋 변환된 파일들:")
        web_files = [f for f in os.listdir(video_dir) if f.startswith('web_') and f.endswith('.mp4')]
        for web_file in web_files[:5]:  # 처음 5개만 표시
            file_size = os.path.getsize(os.path.join(video_dir, web_file))
            print(f"   - {web_file} ({file_size:,} bytes)")
            print(f"     테스트 URL: http://localhost:5000/media/videos/{web_file}")

def update_database_for_web_videos():
    """데이터베이스에 웹 호환 비디오 정보 업데이트"""
    try:
        from services.database_service import get_fall_events, save_fall_event_with_video
        from datetime import datetime
        
        print("\n🔄 데이터베이스에 웹 호환 비디오 등록 중...")
        
        video_dir = 'saved_videos'
        web_files = [f for f in os.listdir(video_dir) if f.startswith('web_') and f.endswith('.mp4')]
        
        registered = 0
        for web_file in web_files:
            try:
                # 원본 파일명 추출
                original_name = web_file[4:]  # 'web_' 제거
                
                # 파일 정보 가져오기
                file_path = os.path.join(video_dir, web_file)
                stat = os.stat(file_path)
                
                # 파일명에서 시간 추출 시도
                timestamp = datetime.fromtimestamp(stat.st_mtime)
                
                filename_parts = original_name.replace('.mp4', '').split('_')
                if len(filename_parts) >= 3:
                    try:
                        date_part = filename_parts[2]  # 20250927
                        time_part = filename_parts[3]  # 122047
                        
                        year = date_part[:4]
                        month = date_part[4:6]
                        day = date_part[6:8]
                        hour = time_part[:2]
                        minute = time_part[2:4]
                        second = time_part[4:6]
                        
                        datetime_str = f"{year}-{month}-{day} {hour}:{minute}:{second}"
                        timestamp = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                
                # 데이터베이스에 등록
                event_id = save_fall_event_with_video(
                    timestamp=timestamp,
                    confidence=0.90,
                    video_path=file_path
                )
                
                if event_id:
                    registered += 1
                    print(f"   ✅ {web_file} 등록 완료 (ID: {event_id})")
                
            except Exception as e:
                print(f"   ❌ {web_file} 등록 실패: {e}")
        
        print(f"\n✅ 웹 호환 비디오 {registered}개 데이터베이스 등록 완료!")
        
    except ImportError:
        print("\n⚠️ 데이터베이스 서비스를 사용할 수 없어 등록을 건너뜁니다.")

if __name__ == "__main__":
    print("🎬 기존 비디오 웹 호환 변환 도구")
    print("=" * 60)
    
    # 1. 비디오 변환
    convert_videos_to_web_compatible()
    
    # 2. 데이터베이스 업데이트
    update_database_for_web_videos()
    
    print("\n🎯 모든 작업 완료!")
    print("React 앱에서 'web_' 접두사가 붙은 파일들을 테스트해보세요.")
