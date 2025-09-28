import os
import shutil
from datetime import datetime

def clean_all_except_working_video():
    """web_test_h264.mp4만 남기고 모든 비디오 파일 삭제"""
    video_dir = 'saved_videos'
    keep_file = 'web_test_h264.mp4'
    
    if not os.path.exists(video_dir):
        print("saved_videos 폴더가 없습니다.")
        return
    
    print("🧹 비디오 파일 전체 정리")
    print("=" * 40)
    
    # 모든 비디오 파일 찾기
    all_videos = []
    for filename in os.listdir(video_dir):
        if filename.lower().endswith(('.mp4', '.avi')):
            file_path = os.path.join(video_dir, filename)
            file_size = os.path.getsize(file_path)
            all_videos.append({
                'name': filename,
                'path': file_path,
                'size': file_size
            })
    
    # 보존할 파일과 삭제할 파일 분리
    keep_files = []
    delete_files = []
    
    for video in all_videos:
        if video['name'] == keep_file:
            keep_files.append(video)
        else:
            delete_files.append(video)
    
    print(f"📊 총 비디오 파일: {len(all_videos)}개")
    print(f"📌 보존: {len(keep_files)}개")
    print(f"🗑️ 삭제 예정: {len(delete_files)}개")
    
    if keep_files:
        print(f"\n✅ 보존할 파일:")
        for video in keep_files:
            print(f"   - {video['name']} ({video['size']/1024:.0f} KB)")
    
    if delete_files:
        total_delete_size = sum(v['size'] for v in delete_files)
        print(f"\n🗑️ 삭제할 파일들:")
        print(f"   총 {len(delete_files)}개 파일, {total_delete_size/1024/1024:.1f} MB")
        
        # 처음 5개만 표시
        for video in delete_files[:5]:
            print(f"   - {video['name']} ({video['size']/1024:.0f} KB)")
        if len(delete_files) > 5:
            print(f"   ... 외 {len(delete_files)-5}개")
    
    return keep_files, delete_files

def execute_cleanup():
    """실제 삭제 실행"""
    keep_files, delete_files = clean_all_except_working_video()
    
    if not delete_files:
        print("\n삭제할 파일이 없습니다.")
        return
    
    # 백업 폴더 생성
    backup_dir = 'backup_deleted_videos'
    os.makedirs(backup_dir, exist_ok=True)
    
    print(f"\n🔄 삭제 시작...")
    
    deleted_count = 0
    total_freed = 0
    
    for video in delete_files:
        try:
            # 백업 복사
            backup_path = os.path.join(backup_dir, video['name'])
            shutil.copy2(video['path'], backup_path)
            
            # 원본 삭제
            os.remove(video['path'])
            
            deleted_count += 1
            total_freed += video['size']
            
            if deleted_count % 10 == 0:  # 10개마다 진행상황 출력
                print(f"   진행: {deleted_count}/{len(delete_files)} 개 삭제됨")
                
        except Exception as e:
            print(f"   ❌ 삭제 실패: {video['name']} - {e}")
    
    print(f"\n✅ 정리 완료!")
    print(f"   삭제된 파일: {deleted_count}개")
    print(f"   확보된 용량: {total_freed/1024/1024:.1f} MB")
    print(f"   백업 위치: {backup_dir}")
    
    # 최종 상태 확인
    remaining_videos = [f for f in os.listdir('saved_videos') if f.lower().endswith(('.mp4', '.avi'))]
    print(f"   남은 비디오: {len(remaining_videos)}개")
    
    if remaining_videos:
        print(f"   남은 파일들:")
        for filename in remaining_videos:
            file_path = os.path.join('saved_videos', filename)
            file_size = os.path.getsize(file_path)
            print(f"     - {filename} ({file_size/1024:.0f} KB)")

if __name__ == "__main__":
    print("🧹 SafeFall 비디오 정리 도구")
    print("web_test_h264.mp4만 남기고 모든 비디오 파일을 삭제합니다.")
    print("삭제된 파일들은 backup_deleted_videos 폴더에 백업됩니다.")
    print("=" * 60)
    
    # 미리보기
    keep_files, delete_files = clean_all_except_working_video()
    
    if delete_files:
        print(f"\n⚠️ 주의: {len(delete_files)}개 파일이 삭제됩니다!")
        
        # 자동 실행 (5초 후)
        import time
        print("5초 후 자동으로 삭제를 시작합니다...")
        print("중단하려면 Ctrl+C를 누르세요.")
        
        try:
            for i in range(5, 0, -1):
                print(f"삭제 시작까지: {i}초...")
                time.sleep(1)
            
            execute_cleanup()
            
        except KeyboardInterrupt:
            print("\n❌ 사용자에 의해 취소되었습니다.")
    else:
        print("\n삭제할 파일이 없습니다.")
