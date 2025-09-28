#!/usr/bin/env python3
"""데이터베이스 동기화 수정 스크립트"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database_service import (
    init_database, 
    save_fall_event_with_video, 
    get_fall_events,
    get_fall_events_by_trigger
)
from datetime import datetime
import sqlite3

def fix_database_sync():
    """데이터베이스 동기화 수정"""
    print("🔧 SafeFall 데이터베이스 동기화 수정")
    print("=" * 60)
    
    # 1. 데이터베이스 초기화
    print("1️⃣ 데이터베이스 초기화...")
    if not init_database():
        print("❌ 데이터베이스 초기화 실패")
        return False
    print("✅ 데이터베이스 초기화 완료")
    
    # 2. saved_videos 디렉토리 확인
    video_dir = 'saved_videos'
    if not os.path.exists(video_dir):
        print(f"❌ {video_dir} 디렉토리가 존재하지 않습니다")
        return False
    
    # 3. 디스크 파일 목록 생성
    print("2️⃣ 디스크 파일 스캔...")
    video_files = []
    for filename in os.listdir(video_dir):
        if filename.lower().endswith(('.mp4', '.avi')):
            file_path = os.path.join(video_dir, filename)
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                video_files.append({
                    'filename': filename,
                    'path': file_path,
                    'size': stat.st_size,
                    'mtime': datetime.fromtimestamp(stat.st_mtime)
                })
    
    video_files.sort(key=lambda x: x['mtime'], reverse=True)
    print(f"📁 발견된 비디오 파일: {len(video_files)}개")
    
    # 4. 데이터베이스 현재 상태 확인
    print("3️⃣ 데이터베이스 상태 확인...")
    db_events = get_fall_events(1000)
    db_filenames = set()
    for event in db_events:
        if event.get('video_filename'):
            db_filenames.add(event['video_filename'])
    
    print(f"💾 DB 등록된 비디오: {len(db_filenames)}개")
    
    # 5. 누락된 파일들 찾기
    print("4️⃣ 누락된 파일 분석...")
    missing_files = []
    for video in video_files:
        if video['filename'] not in db_filenames:
            missing_files.append(video)
    
    print(f"🚨 DB에 누락된 파일: {len(missing_files)}개")
    
    if len(missing_files) == 0:
        print("✅ 모든 파일이 이미 동기화되어 있습니다!")
        return True
    
    # 6. 누락된 파일들 등록
    print("5️⃣ 누락된 파일들 등록 시작...")
    
    registered = 0
    failed = 0
    
    for i, video in enumerate(missing_files, 1):
        try:
            # 파일명에서 타임스탬프 추출 시도
            timestamp = video['mtime']  # 기본값: 파일 수정시간
            
            # fall_detection_20250927_155851.mp4 형식 파싱
            if video['filename'].startswith('fall_detection_'):
                parts = video['filename'].replace('.mp4', '').replace('.avi', '').split('_')
                if len(parts) >= 3:
                    try:
                        date_part = parts[2]  # 20250927
                        time_part = parts[3]  # 155851
                        
                        year = date_part[:4]
                        month = date_part[4:6]
                        day = date_part[6:8]
                        hour = time_part[:2]
                        minute = time_part[2:4]
                        second = time_part[4:6]
                        
                        datetime_str = f"{year}-{month}-{day} {hour}:{minute}:{second}"
                        timestamp = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        pass  # 파싱 실패시 기본값 사용
            
            # DB에 등록
            event_id = save_fall_event_with_video(
                timestamp=timestamp,
                confidence=0.90,
                video_path=video['path']
            )
            
            if event_id:
                print(f"   ✅ [{i:2d}/{len(missing_files)}] {video['filename']} -> ID:{event_id}")
                registered += 1
            else:
                print(f"   ❌ [{i:2d}/{len(missing_files)}] {video['filename']} 등록 실패")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ [{i:2d}/{len(missing_files)}] {video['filename']} 오류: {e}")
            failed += 1
    
    # 7. 결과 요약
    print("\n📊 동기화 결과:")
    print(f"   📁 총 파일 수: {len(video_files)}")
    print(f"   💾 기존 DB 등록: {len(db_filenames)}")
    print(f"   🚨 누락된 파일: {len(missing_files)}")
    print(f"   ✅ 새로 등록: {registered}")
    print(f"   ❌ 실패: {failed}")
    
    if registered > 0:
        print(f"\n🎉 {registered}개 파일이 성공적으로 데이터베이스에 등록되었습니다!")
        print("📱 프론트엔드를 새로고침하면 새로운 비디오들이 표시됩니다.")
    
    return registered > 0

def check_database_integrity():
    """데이터베이스 무결성 확인"""
    print("\n🔍 데이터베이스 무결성 확인")
    print("-" * 40)
    
    try:
        # 1. 테이블 구조 확인
        conn = sqlite3.connect('safefall.db')
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(fall_events)")
        columns = cursor.fetchall()
        
        print("📋 fall_events 테이블 구조:")
        for col in columns:
            print(f"   - {col[1]} {col[2]} {'NOT NULL' if col[3] else ''}")
        
        # 2. 데이터 통계
        cursor.execute("SELECT COUNT(*) FROM fall_events")
        total_events = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fall_events WHERE video_filename IS NOT NULL")
        video_events = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fall_events WHERE processed = 1")
        processed_events = cursor.fetchone()[0]
        
        print(f"\n📈 데이터 통계:")
        print(f"   - 총 이벤트: {total_events}개")
        print(f"   - 비디오 연결: {video_events}개")
        print(f"   - 처리 완료: {processed_events}개")
        print(f"   - 미처리: {total_events - processed_events}개")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 무결성 확인 실패: {e}")
        return False

if __name__ == "__main__":
    print("🚀 SafeFall 데이터베이스 동기화 수정 도구")
    print("=" * 70)
    
    # 동기화 수행
    success = fix_database_sync()
    
    # 무결성 확인
    check_database_integrity()
    
    if success:
        print(f"\n🎯 수정 완료! 프론트엔드에서 확인해보세요.")
    else:
        print(f"\n⚠️  문제가 해결되지 않았습니다. 로그를 확인해주세요.")
