#!/usr/bin/env python3
"""데이터베이스 테이블에 trigger_type 컬럼 추가"""
import sqlite3
import os

def add_trigger_type_column():
    """fall_events 테이블에 trigger_type 컬럼 추가"""
    db_path = "safefall.db"
    
    if not os.path.exists(db_path):
        print("데이터베이스 파일이 없습니다")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # trigger_type 컬럼 추가 (이미 있으면 오류 무시)
        try:
            cursor.execute("ALTER TABLE fall_events ADD COLUMN trigger_type TEXT DEFAULT 'auto'")
            print("✅ trigger_type 컬럼 추가 완료")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("✅ trigger_type 컬럼이 이미 존재합니다")
            else:
                raise e
        
        # 기존 데이터에서 device_id가 manual이면 trigger_type을 manual로 업데이트
        cursor.execute("""
            UPDATE fall_events 
            SET trigger_type = 'manual' 
            WHERE device_id IN ('manual', 'manual_trigger')
        """)
        manual_updated = cursor.rowcount
        
        # 나머지는 auto로 설정
        cursor.execute("""
            UPDATE fall_events 
            SET trigger_type = 'auto' 
            WHERE trigger_type IS NULL OR trigger_type = ''
        """)
        auto_updated = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"수동 트리거로 업데이트: {manual_updated}개")
        print(f"자동 감지로 업데이트: {auto_updated}개")
        
    except Exception as e:
        print(f"데이터베이스 업데이트 오류: {e}")

if __name__ == "__main__":
    add_trigger_type_column()
