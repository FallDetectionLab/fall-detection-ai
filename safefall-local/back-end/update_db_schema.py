#!/usr/bin/env python3
"""데이터베이스 스키마 업데이트 스크립트"""
import sqlite3
import os

db_path = "safefall.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== 데이터베이스 스키마 업데이트 ===")
    
    # 현재 스키마 확인
    cursor.execute("PRAGMA table_info(fall_events);")
    current_columns = [col[1] for col in cursor.fetchall()]
    print(f"현재 컬럼들: {current_columns}")
    
    # video_filename 컬럼이 없다면 추가
    if 'video_filename' not in current_columns:
        print("video_filename 컬럼을 추가합니다...")
        cursor.execute("ALTER TABLE fall_events ADD COLUMN video_filename TEXT;")
        print("✅ video_filename 컬럼 추가됨")
    
    # device_id 컬럼이 없다면 추가
    if 'device_id' not in current_columns:
        print("device_id 컬럼을 추가합니다...")
        cursor.execute("ALTER TABLE fall_events ADD COLUMN device_id TEXT DEFAULT 'unknown';")
        print("✅ device_id 컬럼 추가됨")
    
    # title 컬럼이 없다면 추가
    if 'title' not in current_columns:
        print("title 컬럼을 추가합니다...")
        cursor.execute("ALTER TABLE fall_events ADD COLUMN title TEXT;")
        print("✅ title 컬럼 추가됨")
    
    # description 컬럼이 없다면 추가
    if 'description' not in current_columns:
        print("description 컬럼을 추가합니다...")
        cursor.execute("ALTER TABLE fall_events ADD COLUMN description TEXT;")
        print("✅ description 컬럼 추가됨")
    
    # created_at 컬럼이 없다면 추가
    if 'created_at' not in current_columns:
        print("created_at 컬럼을 추가합니다...")
        cursor.execute("ALTER TABLE fall_events ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        print("✅ created_at 컬럼 추가됨")
    
    conn.commit()
    
    # 업데이트된 스키마 확인
    cursor.execute("PRAGMA table_info(fall_events);")
    updated_columns = cursor.fetchall()
    print(f"업데이트된 테이블 구조:")
    for col in updated_columns:
        print(f"  - {col[1]} ({col[2]})")
    
    conn.close()
    print("✅ 데이터베이스 스키마 업데이트 완료")
    
except Exception as e:
    print(f"❌ 스키마 업데이트 실패: {e}")
    if conn:
        conn.rollback()
        conn.close()
