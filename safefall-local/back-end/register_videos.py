#!/usr/bin/env python3
"""실제 저장된 비디오 파일들을 데이터베이스에 등록하는 스크립트"""
import sqlite3
import os
from datetime import datetime
import re

def register_saved_videos():
    """saved_videos 폴더의 실제 파일들을 데이터베이스에 등록"""
    
    # 데이터베이스 연결
    conn = sqlite3.connect('safefall.db')
    cursor = conn.cursor()
    
    # saved_videos 폴더 확인
    video_dir = 'saved_videos'
    if not os.path.exists(video_dir):
        print(f"❌ {video_dir} 폴더가 없습니다")
        return
    
    # .avi 파일들 찾기
    video_files = [f for f in os.listdir(video_dir) if f.endswith('.avi')]
    video_files.sort()
    
    print(f"📁 {len(video_files)}개의 비디오 파일 발견")
    
    registered_count = 0
    
    for filename in video_files:
        try:
            # 파일명에서 날짜/시간 추출: fall_detection_20250927_105658.avi
            match = re.match(r'fall_detection_(\d{8})_(\d{6})\.avi', filename)
            if not match:
                print(f"⚠️ 파일명 형식이 맞지 않음: {filename}")
                continue
            
            date_str = match.group(1)  # 20250927
            time_str = match.group(2)  # 105658
            
            # 날짜/시간 문자열을 datetime으로 변환
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
            
            timestamp = datetime(year, month, day, hour, minute, second)
            video_path = os.path.join(video_dir, filename)
            
            # 이미 등록된 파일인지 확인
            cursor.execute('SELECT id FROM fall_events WHERE video_filename = ?', (filename,))
            existing = cursor.fetchone()
            
            if existing:
                print(f"⏭️ 이미 등록됨: {filename}")
                continue
            
            # 새 이벤트로 등록
            title = f"낙상 감지 - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            description = f"파일: {filename}"
            
            cursor.execute('''
                INSERT INTO fall_events 
                (timestamp, confidence, video_filename, video_path, device_id, 
                 processed, title, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                0.95,  # 기본 신뢰도
                filename,
                video_path,
                'manual_trigger',  # 수동 트리거로 설정
                False,  # 미처리 상태
                title,
                description,
                timestamp.isoformat()
            ))
            
            registered_count += 1
            print(f"✅ 등록 완료: {filename} -> 이벤트 ID {cursor.lastrowid}")
            
        except Exception as e:
            print(f"❌ {filename} 등록 실패: {e}")
    
    # 변경사항 저장
    conn.commit()
    conn.close()
    
    print(f"\n🎉 총 {registered_count}개 파일이 데이터베이스에 등록되었습니다!")
    
    # 등록 결과 확인
    verify_registration()

def verify_registration():
    """등록 결과 확인"""
    conn = sqlite3.connect('safefall.db')
    cursor = conn.cursor()
    
    # 전체 이벤트 수 확인
    cursor.execute('SELECT COUNT(*) FROM fall_events')
    total_count = cursor.fetchone()[0]
    
    # 수동 트리거 이벤트 수 확인
    cursor.execute("SELECT COUNT(*) FROM fall_events WHERE device_id = 'manual_trigger'")
    manual_count = cursor.fetchone()[0]
    
    # 비디오 파일이 있는 이벤트 수 확인
    cursor.execute('SELECT COUNT(*) FROM fall_events WHERE video_filename IS NOT NULL')
    with_video_count = cursor.fetchone()[0]
    
    # 최근 5개 이벤트 조회
    cursor.execute('''
        SELECT id, timestamp, video_filename, device_id 
        FROM fall_events 
        ORDER BY created_at DESC 
        LIMIT 5
    ''')
    recent_events = cursor.fetchall()
    
    print(f"\n📊 데이터베이스 현황:")
    print(f"- 전체 이벤트: {total_count}개")
    print(f"- 수동 트리거: {manual_count}개")
    print(f"- 비디오 있음: {with_video_count}개")
    
    print(f"\n📋 최근 이벤트 5개:")
    for event in recent_events:
        print(f"- ID {event[0]}: {event[1]} | {event[2]} | {event[3]}")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 실제 저장된 비디오 파일들을 데이터베이스에 등록합니다...")
    register_saved_videos()
