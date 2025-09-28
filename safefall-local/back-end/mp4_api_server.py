#!/usr/bin/env python3
"""
MP4 파일만 반환하는 임시 API 엔드포인트 생성
"""

from flask import Flask, jsonify
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

@app.route('/api/videos/mp4only', methods=['GET'])
def get_mp4_videos_only():
    """MP4 파일만 반환하는 API"""
    try:
        # 데이터베이스에서 모든 이벤트 가져오기
        conn = sqlite3.connect('safefall.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, confidence, video_filename, video_path, 
                   device_id, processed, title, description, created_at
            FROM fall_events 
            WHERE video_filename IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT 100
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        mp4_videos = []
        
        for row in rows:
            video_filename = row['video_filename']
            
            # MP4 파일만 처리
            if not video_filename.lower().endswith('.mp4'):
                continue
            
            # 파일 존재 확인
            video_path = os.path.join('saved_videos', video_filename)
            if not os.path.exists(video_path):
                continue
            
            stat = os.stat(video_path)
            
            mp4_videos.append({
                'id': row['id'],
                'title': row['title'] or f'SafeFall Video - {video_filename}',
                'filename': video_filename,
                'name': video_filename,
                'path': f'/media/videos/{video_filename}',
                'url': f'/media/videos/{video_filename}',
                'size': stat.st_size,
                'created_at': row['created_at'],
                'createdAt': row['created_at'],
                'confidence': row['confidence'] or 0.95,
                'isChecked': bool(row['processed']),
                'processed': bool(row['processed']),
                'trigger_type': 'manual',
                'device_id': row['device_id'] or 'manual_trigger',
                'file_type': 'mp4'
            })
        
        print(f"✅ MP4 파일 {len(mp4_videos)}개 반환")
        
        return jsonify({
            'success': True,
            'videos': mp4_videos,
            'count': len(mp4_videos),
            'filter': 'mp4_only'
        })
        
    except Exception as e:
        print(f"❌ MP4 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'videos': [],
            'count': 0
        }), 500

if __name__ == '__main__':
    print("🎬 MP4 전용 API 서버 시작...")
    print("📡 테스트 URL: http://localhost:5001/api/videos/mp4only")
    app.run(host='0.0.0.0', port=5001, debug=True)
