"""통합 데이터베이스 서비스 (영상 이벤트 통합 관리)"""
import sqlite3
import os
from datetime import datetime
import threading

# 데이터베이스 경로
DATABASE_PATH = "safefall.db"
db_lock = threading.Lock()

def get_db_connection():
    """데이터베이스 연결 반환"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """데이터베이스 초기화"""
    try:        
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 통합된 fall_events 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fall_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    video_filename TEXT,
                    video_path TEXT,
                    device_id TEXT DEFAULT 'unknown',
                    processed BOOLEAN DEFAULT FALSE,
                    title TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 알림 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    type TEXT DEFAULT 'fall_detection',
                    title TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    read BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (event_id) REFERENCES fall_events (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        print("[db] Unified fall_events table initialized")
        return True
    except Exception as e:
        print(f"[db] Database initialization failed: {e}")
        return False

def save_fall_event_with_video(timestamp, confidence, video_path=None, device_id='manual_trigger'):
    """낙상 이벤트를 영상 정보와 함께 저장"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # timestamp 처리
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
                dt = timestamp
            else:
                timestamp_str = str(timestamp)
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                except:
                    dt = datetime.now()
            
            # 비디오 파일명 추출
            video_filename = None
            if video_path:
                video_filename = os.path.basename(video_path)
            
            # 제목과 설명 생성
            title = f"낙상 감지 - {dt.strftime('%Y-%m-%d %H:%M:%S')}"
            description = f"신뢰도: {confidence:.1%}"
            
            # device_id 컬럼이 있는지 확인하고 테이블 구조 업데이트
            cursor.execute("PRAGMA table_info(fall_events)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # device_id 컬럼이 없으면 추가
            if 'device_id' not in columns:
                cursor.execute('ALTER TABLE fall_events ADD COLUMN device_id TEXT DEFAULT "unknown"')
                print("[db] Added device_id column to fall_events table")
            
            # trigger_type 컬럼이 없으면 추가
            if 'trigger_type' not in columns:
                cursor.execute('ALTER TABLE fall_events ADD COLUMN trigger_type TEXT DEFAULT "manual"')
                print("[db] Added trigger_type column to fall_events table")
            
            # 데이터 삽입
            cursor.execute('''
                INSERT INTO fall_events 
                (timestamp, confidence, video_filename, video_path, title, description, processed, device_id, trigger_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp_str, confidence, video_filename, video_path, title, description, False, device_id, 'manual'))
            
            event_id = cursor.lastrowid
            
            # 알림도 함께 생성
            cursor.execute('''
                INSERT INTO notifications (event_id, title, message)
                VALUES (?, ?, ?)
            ''', (event_id, title, description))
            
            conn.commit()
            conn.close()
            
        print(f"[db] Fall event saved: id={event_id}, confidence={confidence}, video={video_filename}, device={device_id}")
        return event_id
        
    except Exception as e:
        print(f"[db] Failed to save fall event: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_fall_event_legacy(timestamp, confidence, video_path=None):
    """기존 방식 호환용"""
    return save_fall_event_with_video(timestamp, confidence, video_path)

def save_fall_event(confidence, bbox=None, video_path=None, device_id='unknown', 
                   filename=None, duration_sec=0.0, trigger_reason='fall_detected'):
    """낙상 이벤트 저장 (외부 호출용)"""
    timestamp = datetime.now()
    
    # video_path에서 filename 추출
    if video_path and not filename:
        filename = os.path.basename(video_path)
    
    return save_fall_event_with_video(timestamp, confidence, video_path)

def get_fall_events(limit=50):
    """낙상 이벤트 목록 조회"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, timestamp, confidence, video_filename, video_path, 
                       device_id, processed, title, description, created_at
                FROM fall_events 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
        events = []
        for row in rows:
            events.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'confidence': row['confidence'],
                'video_filename': row['video_filename'],
                'video_path': row['video_path'],
                'device_id': row['device_id'] or 'unknown',
                'processed': bool(row['processed']),
                'title': row['title'],
                'description': row['description'],
                'created_at': row['created_at']
            })
            
        return events
        
    except Exception as e:
        print(f"[db] Failed to get fall events: {e}")
        return []

def get_fall_videos(limit=50):
    """낙상 영상 목록 조회 (별칭)"""
    return get_fall_events(limit)

def mark_event_processed(event_id):
    """이벤트를 처리됨으로 표시"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE fall_events 
                SET processed = TRUE 
                WHERE id = ?
            ''', (event_id,))
            
            conn.commit()
            conn.close()
            
        return True
    except Exception as e:
        print(f"[db] Failed to mark event as processed: {e}")
        return False

def get_dashboard_stats():
    """대시보드 통계 조회"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 전체 이벤트 수
            cursor.execute('SELECT COUNT(*) as total FROM fall_events')
            total_events = cursor.fetchone()['total']
            
            # 오늘 이벤트 수  
            cursor.execute('''
                SELECT COUNT(*) as today 
                FROM fall_events 
                WHERE DATE(created_at) = DATE('now')
            ''')
            today_events = cursor.fetchone()['today']
            
            # 처리되지 않은 이벤트 수
            cursor.execute('''
                SELECT COUNT(*) as unprocessed 
                FROM fall_events 
                WHERE processed = FALSE
            ''')
            unprocessed_events = cursor.fetchone()['unprocessed']
            
            conn.close()
            
        return {
            'total_events': total_events,
            'today_events': today_events,
            'unprocessed_events': unprocessed_events
        }
        
    except Exception as e:
        print(f"[db] Failed to get dashboard stats: {e}")
        return {
            'total_events': 0,
            'today_events': 0,
            'unprocessed_events': 0
        }

def get_fall_events_by_trigger(trigger_type='manual', limit=50):
    """트리거 타입별 낙상 이벤트 조회"""
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # trigger_type 컬럼이 있는지 확인
            cursor.execute("PRAGMA table_info(fall_events)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'trigger_type' in columns:
                # trigger_type 컬럼이 있으면 필터링
                cursor.execute('''
                    SELECT id, timestamp, confidence, video_filename, video_path, 
                           device_id, processed, title, description, created_at, trigger_type
                    FROM fall_events 
                    WHERE trigger_type = ? AND video_path IS NOT NULL
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (trigger_type, limit))
            else:
                # trigger_type 컬럼이 없으면 device_id로 판단
                if trigger_type == 'manual':
                    cursor.execute('''
                        SELECT id, timestamp, confidence, video_filename, video_path, 
                               device_id, processed, title, description, created_at
                        FROM fall_events 
                        WHERE device_id IN ('manual', 'manual_trigger') AND video_path IS NOT NULL
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (limit,))
                else:
                    cursor.execute('''
                        SELECT id, timestamp, confidence, video_filename, video_path, 
                               device_id, processed, title, description, created_at
                        FROM fall_events 
                        WHERE device_id NOT IN ('manual', 'manual_trigger') AND video_path IS NOT NULL
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
        events = []
        for row in rows:
            event = {
                'id': row['id'],
                'timestamp': row['timestamp'],
                'confidence': row['confidence'],
                'video_filename': row['video_filename'],
                'video_path': row['video_path'],
                'device_id': row['device_id'] or 'unknown',
                'processed': bool(row['processed']),
                'title': row['title'],
                'description': row['description'],
                'created_at': row['created_at']
            }
            
            # trigger_type 컬럼이 있으면 추가
            if 'trigger_type' in columns:
                event['trigger_type'] = row['trigger_type']
            else:
                # device_id로 판단
                if row['device_id'] in ['manual', 'manual_trigger']:
                    event['trigger_type'] = 'manual'
                else:
                    event['trigger_type'] = 'auto'
            
            events.append(event)
            
        print(f"[db] Found {len(events)} events with trigger_type={trigger_type}")
        return events
        
    except Exception as e:
        print(f"[db] Failed to get events by trigger: {e}")
        return []