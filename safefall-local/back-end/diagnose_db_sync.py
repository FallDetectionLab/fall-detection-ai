#!/usr/bin/env python3
"""데이터베이스와 파일시스템 상태 비교"""
import sqlite3
import os
from datetime import datetime

def check_database_vs_filesystem():
    """데이터베이스와 파일시스템 비교"""
    print("🔍 SafeFall 데이터베이스 vs 파일시스템 비교")
    print("=" * 60)
    
    # 1. 파일시스템 확인
    saved_videos_dir = "saved_videos"
    if not os.path.exists(saved_videos_dir):
        print(f"❌ {saved_videos_dir} 디렉토리가 없습니다!")
        return
    
    video_files = []
    for filename in os.listdir(saved_videos_dir):
        if filename.lower().endswith(('.mp4', '.avi')):
            file_path = os.path.join(saved_videos_dir, filename)
            stat = os.stat(file_path)
            video_files.append({
                'filename': filename,
                'size': stat.st_size,
                'mtime': datetime.fromtimestamp(stat.st_mtime)
            })
    
    video_files.sort(key=lambda x: x['mtime'], reverse=True)
    
    print(f"📁 파일시스템 영상 파일: {len(video_files)}개")
    print("📋 최근 10개 파일:")
    for i, video in enumerate(video_files[:10], 1):
        size_mb = video['size'] / (1024 * 1024)
        print(f"  {i:2d}. {video['filename']} ({size_mb:.1f}MB, {video['mtime'].strftime('%Y-%m-%d %H:%M:%S')})")
    
    # 2. 데이터베이스 확인
    db_path = "safefall.db"
    if not os.path.exists(db_path):
        print(f"\n❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fall_events';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print(f"\n❌ fall_events 테이블이 존재하지 않습니다!")
            conn.close()
            return
        
        # 전체 이벤트 수
        cursor.execute("SELECT COUNT(*) as count FROM fall_events")
        total_events = cursor.fetchone()['count']
        
        # 비디오가 있는 이벤트 수
        cursor.execute("SELECT COUNT(*) as count FROM fall_events WHERE video_filename IS NOT NULL")
        video_events = cursor.fetchone()['count']
        
        # 최근 10개 이벤트 조회
        cursor.execute("""
            SELECT id, timestamp, video_filename, device_id, created_at
            FROM fall_events 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        db_events = cursor.fetchall()
        
        print(f"\n💾 데이터베이스 이벤트: {total_events}개")
        print(f"🎬 비디오 연결된 이벤트: {video_events}개")
        print("📋 최근 10개 DB 이벤트:")
        
        for i, event in enumerate(db_events, 1):
            print(f"  {i:2d}. ID:{event['id']} {event['video_filename'] or 'NO VIDEO'} ({event['created_at']})")
        
        # 3. 매칭 분석
        print(f"\n🔍 매칭 분석:")
        
        # DB에 있는 파일명들
        cursor.execute("SELECT DISTINCT video_filename FROM fall_events WHERE video_filename IS NOT NULL")
        db_filenames = set(row['video_filename'] for row in cursor.fetchall())
        
        # 파일시스템에 있는 파일명들
        fs_filenames = set(video['filename'] for video in video_files)
        
        # 누락된 파일들 (파일시스템에는 있지만 DB에는 없음)
        missing_in_db = fs_filenames - db_filenames
        
        # DB에는 있지만 파일시스템에는 없는 것들
        missing_in_fs = db_filenames - fs_filenames
        
        print(f"  📁 파일시스템 파일: {len(fs_filenames)}개")
        print(f"  💾 DB 등록된 파일: {len(db_filenames)}개")
        print(f"  ❗ DB에 누락된 파일: {len(missing_in_db)}개")
        print(f"  ❗ 파일이 없는 DB 레코드: {len(missing_in_fs)}개")
        
        if missing_in_db:
            print(f"\n🚨 DB에 누락된 파일들 (최근 10개):")
            missing_files = [video for video in video_files if video['filename'] in missing_in_db]
            missing_files.sort(key=lambda x: x['mtime'], reverse=True)
            
            for i, video in enumerate(missing_files[:10], 1):
                print(f"  {i:2d}. {video['filename']} ({video['mtime'].strftime('%Y-%m-%d %H:%M:%S')})")
        
        conn.close()
        
        # 4. 결론
        print(f"\n📊 결론:")
        if len(missing_in_db) > 0:
            print(f"  ⚠️  {len(missing_in_db)}개의 영상이 데이터베이스에 등록되지 않았습니다!")
            print(f"  🔧 동기화가 필요합니다.")
        else:
            print(f"  ✅ 모든 영상이 데이터베이스에 등록되어 있습니다.")
            
    except Exception as e:
        print(f"❌ 데이터베이스 확인 오류: {e}")

if __name__ == "__main__":
    check_database_vs_filesystem()
