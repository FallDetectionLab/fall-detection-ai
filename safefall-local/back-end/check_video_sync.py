import os
from datetime import datetime

def check_video_sync():
    """디스크 파일과 데이터베이스 동기화 상태 확인"""
    video_dir = 'saved_videos'
    
    print("🔍 비디오 파일 동기화 상태 확인")
    print("=" * 50)
    
    # 1. 디스크에 있는 파일들 확인
    disk_files = []
    if os.path.exists(video_dir):
        for filename in sorted(os.listdir(video_dir)):
            if filename.lower().endswith(('.mp4', '.avi')):
                file_path = os.path.join(video_dir, filename)
                file_size = os.path.getsize(file_path)
                file_mtime = os.path.getmtime(file_path)
                
                disk_files.append({
                    'name': filename,
                    'path': file_path,
                    'size': file_size,
                    'mtime': file_mtime,
                    'date': datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    print(f"💾 디스크 파일: {len(disk_files)}개")
    for i, file_info in enumerate(disk_files, 1):
        print(f"   {i}. {file_info['name']} ({file_info['size']:,} bytes, {file_info['date']})")
    
    # 2. 데이터베이스에 등록된 파일들 확인
    try:
        from services.database_service import get_fall_events
        db_events = get_fall_events(20)  # 최근 20개
        
        print(f"\n🗄️ 데이터베이스 이벤트: {len(db_events)}개")
        for i, event in enumerate(db_events, 1):
            filename = event.get('video_filename', 'N/A')
            timestamp = event.get('timestamp', 'N/A')
            event_id = event.get('id', 'N/A')
            print(f"   {i}. ID:{event_id} - {filename} ({timestamp})")
            
        # 3. 매칭 확인
        print(f"\n🔗 매칭 상태:")
        disk_names = set(f['name'] for f in disk_files)
        db_names = set(event.get('video_filename', '') for event in db_events if event.get('video_filename'))
        
        # 디스크에는 있지만 DB에 없는 파일들
        missing_in_db = disk_names - db_names
        if missing_in_db:
            print(f"   ❌ DB에 없는 파일들: {len(missing_in_db)}개")
            for filename in missing_in_db:
                print(f"      - {filename}")
        
        # DB에는 있지만 디스크에 없는 파일들
        missing_on_disk = db_names - disk_names
        if missing_on_disk:
            print(f"   ❌ 디스크에 없는 파일들: {len(missing_on_disk)}개")
            for filename in missing_on_disk:
                print(f"      - {filename}")
        
        # 정상적으로 매칭되는 파일들
        matched = disk_names & db_names
        if matched:
            print(f"   ✅ 정상 매칭: {len(matched)}개")
            for filename in matched:
                print(f"      - {filename}")
                
    except Exception as e:
        print(f"\n❌ 데이터베이스 확인 실패: {e}")
        db_events = []
    
    return disk_files, db_events

def register_missing_videos():
    """DB에 없는 비디오 파일들을 데이터베이스에 등록"""
    try:
        from services.database_service import save_fall_event_with_video
        
        disk_files, db_events = check_video_sync()
        
        # DB에 등록된 파일명들
        db_filenames = set(event.get('video_filename', '') for event in db_events if event.get('video_filename'))
        
        # 등록이 필요한 파일들
        files_to_register = []
        for file_info in disk_files:
            if file_info['name'] not in db_filenames:
                files_to_register.append(file_info)
        
        if not files_to_register:
            print(f"\n✅ 모든 파일이 이미 DB에 등록되어 있습니다.")
            return
        
        print(f"\n📝 DB에 등록할 파일: {len(files_to_register)}개")
        
        registered = 0
        for file_info in files_to_register:
            try:
                # 파일 수정 시간을 기준으로 타임스탬프 생성
                timestamp = datetime.fromtimestamp(file_info['mtime'])
                
                # 데이터베이스에 등록
                event_id = save_fall_event_with_video(
                    timestamp=timestamp,
                    confidence=0.90,  # 기본 신뢰도
                    video_path=file_info['path']
                )
                
                if event_id:
                    print(f"   ✅ 등록 성공: {file_info['name']} (ID: {event_id})")
                    registered += 1
                else:
                    print(f"   ❌ 등록 실패: {file_info['name']}")
                    
            except Exception as e:
                print(f"   ❌ 등록 오류: {file_info['name']} - {e}")
        
        print(f"\n🎯 등록 완료: {registered}/{len(files_to_register)}개")
        
        if registered > 0:
            print(f"✅ 프론트엔드를 새로고침하면 새로운 비디오들이 표시됩니다.")
            
    except Exception as e:
        print(f"❌ 등록 프로세스 실패: {e}")

if __name__ == "__main__":
    print("🔄 SafeFall 비디오 동기화 도구")
    print("=" * 60)
    
    # 1. 현재 상태 확인
    disk_files, db_events = check_video_sync()
    
    # 2. 누락된 파일들 자동 등록
    if disk_files:
        print(f"\n" + "=" * 60)
        register_missing_videos()
        
        # 3. 최종 확인
        print(f"\n" + "=" * 60)
        print("🔍 최종 동기화 상태:")
        check_video_sync()
    else:
        print(f"\n📂 saved_videos 폴더에 비디오 파일이 없습니다.")
