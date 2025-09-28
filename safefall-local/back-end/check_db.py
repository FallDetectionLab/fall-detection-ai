#!/usr/bin/env python3
"""데이터베이스 상태 확인 스크립트"""
import sqlite3
import os

db_path = "safefall.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== 데이터베이스 상태 확인 ===")
    
    # 테이블 목록
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"테이블 목록: {tables}")
    
    # fall_events 테이블 구조
    cursor.execute("PRAGMA table_info(fall_events);")
    columns = cursor.fetchall()
    print(f"fall_events 테이블 구조:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # fall_events 데이터 개수
    cursor.execute("SELECT COUNT(*) FROM fall_events;")
    count = cursor.fetchone()[0]
    print(f"fall_events 총 개수: {count}")
    
    # 최근 5개 이벤트
    cursor.execute("SELECT id, timestamp, confidence, video_filename, device_id, processed FROM fall_events ORDER BY created_at DESC LIMIT 5;")
    recent = cursor.fetchall()
    print(f"최근 5개 이벤트:")
    for event in recent:
        print(f"  - ID: {event[0]}, 시간: {event[1]}, 신뢰도: {event[2]}, 파일: {event[3]}, 기기: {event[4]}, 처리됨: {event[5]}")
    
    # notifications 테이블도 확인
    cursor.execute("SELECT COUNT(*) FROM notifications;")
    notif_count = cursor.fetchone()[0]
    print(f"알림 개수: {notif_count}")
    
    conn.close()
    print("✅ 데이터베이스 확인 완료")
    
except Exception as e:
    print(f"❌ 데이터베이스 확인 실패: {e}")
