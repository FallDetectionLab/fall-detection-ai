#!/bin/bash
# 백업 및 복원 스크립트

BACKUP_DIR="/opt/app/backups"
DB_PATH="/opt/app/incidents.db"
VIDEO_DIR="/opt/app/incident_videos"
DATE=$(date +%Y%m%d_%H%M%S)

# 백업 함수
backup() {
    echo "백업 시작..."
    
    # 백업 디렉토리 생성
    sudo mkdir -p $BACKUP_DIR
    
    # 데이터베이스 백업
    sudo sqlite3 $DB_PATH ".backup $BACKUP_DIR/incidents_$DATE.db"
    
    # 영상 파일 백업 (선택적 - 용량이 클 수 있음)
    if [ "$1" = "--include-videos" ]; then
        sudo tar -czf $BACKUP_DIR/videos_$DATE.tar.gz -C $VIDEO_DIR .
        echo "영상 파일 백업 완료"
    fi
    
    echo "백업 완료: $BACKUP_DIR/"
    ls -la $BACKUP_DIR/
}

# 복원 함수
restore() {
    if [ -z "$1" ]; then
        echo "사용법: $0 restore <backup_date>"
        echo "사용 가능한 백업:"
        ls -la $BACKUP_DIR/incidents_*.db 2>/dev/null | awk '{print $9}' | sed 's/.*incidents_//' | sed 's/.db//'
        return 1
    fi
    
    BACKUP_FILE="$BACKUP_DIR/incidents_$1.db"
    
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "백업 파일을 찾을 수 없습니다: $BACKUP_FILE"
        return 1
    fi
    
    # 서비스 중지
    sudo systemctl stop security-camera.service
    
    # 기존 DB 백업
    sudo cp $DB_PATH $DB_PATH.backup_$(date +%Y%m%d_%H%M%S)
    
    # 복원
    sudo cp $BACKUP_FILE $DB_PATH
    sudo chown www-data:www-data $DB_PATH
    
    # 서비스 재시작
    sudo systemctl start security-camera.service
    
    echo "복원 완료"
}

# 로그 정리 함수
cleanup_logs() {
    echo "로그 정리 중..."
    
    # 7일 이상 된 로그 파일 삭제
    sudo find /var/log/gunicorn/ -name "*.log" -mtime +7 -delete
    sudo find /var/log/nginx/ -name "*security_camera*" -mtime +7 -delete
    
    # 30일 이상 된 백업 삭제
    sudo find $BACKUP_DIR -name "*.db" -mtime +30 -delete
    sudo find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
    
    echo "로그 정리 완료"
}

case "$1" in
    backup)
        backup $2
        ;;
    restore)
        restore $2
        ;;
    cleanup)
        cleanup_logs
        ;;
    *)
        echo "사용법: $0 {backup|restore|cleanup}"
        echo "  backup [--include-videos] : 데이터베이스 백업 (선택적으로 영상 파일 포함)"
        echo "  restore <date>            : 특정 날짜의 백업 복원"
        echo "  cleanup                   : 오래된 로그와 백업 정리"
        exit 1
        ;;
esac