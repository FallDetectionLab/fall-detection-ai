#!/usr/bin/env python3
"""데이터베이스의 모든 낙상 이벤트 삭제"""
import sqlite3
import os

def clear_database():
    """fall_events 테이블의 모든 데이터 삭제"""
    db_path = "safefall.db"
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 모든 낙상 이벤트 삭제
            cursor.execute("DELETE FROM fall_events")
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"데이터베이스에서 {deleted_count}개 이벤트 삭제 완료")
        except Exception as e:
            print(f"데이터베이스 삭제 오류: {e}")
    else:
        print("데이터베이스 파일이 없습니다")

if __name__ == "__main__":
    clear_database()
