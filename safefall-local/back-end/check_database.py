#!/usr/bin/env python3
"""데이터베이스 테이블 구조와 데이터 확인"""
import sqlite3
import os

def check_database():
    """데이터베이스 테이블 구조와 데이터 확인"""
    db_path = "safefall.db"
    
    if not os.path.exists(db_path):
        print("데이터베이스 파일이 없습니다")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("=== 테이블 목록 ===")
        for table in tables:
            print(f"- {table[0]}")
        
        # fall_events 테이블 구조 확인
        print("\n=== fall_events 테이블 구조 ===")
        cursor.execute("PRAGMA table_info(fall_events);")
        columns = cursor.fetchall()
        for col in columns:
            print(f"- {col[1]} ({col[2]}) - NULL: {col[3]==0} - Default: {col[4]}")
        
        # 최근 데이터 10개 확인
        print("\n=== 최근 데이터 10개 ===")
        cursor.execute("SELECT * FROM fall_events ORDER BY timestamp DESC LIMIT 10;")
        rows = cursor.fetchall()
        
        column_names = [description[0] for description in cursor.description]
        print("컬럼:", column_names)
        
        for i, row in enumerate(rows):
            print(f"Row {i+1}: {row}")
        
        # 통계
        cursor.execute("SELECT COUNT(*) FROM fall_events;")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fall_events WHERE video_path IS NOT NULL;")
        with_video_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fall_events WHERE device_id = 'manual_trigger' OR device_id = 'manual';")
        manual_count = cursor.fetchone()[0]
        
        print(f"\n=== 통계 ===")
        print(f"전체 이벤트: {total_count}")
        print(f"비디오 있는 이벤트: {with_video_count}")
        print(f"수동 트리거 이벤트: {manual_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"데이터베이스 확인 오류: {e}")

if __name__ == "__main__":
    check_database()
