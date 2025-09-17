#!/bin/bash
# 시스템 모니터링 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 서비스 상태 확인
check_service() {
    local service=$1
    if systemctl is-active --quiet $service; then
        echo -e "${GREEN}✓${NC} $service is running"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not running"
        return 1
    fi
}

# 디스크 사용량 확인
check_disk_usage() {
    local path=$1
    local threshold=${2:-80}
    local usage=$(df $path | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ $usage -gt $threshold ]; then
        echo -e "${RED}✗${NC} Disk usage at $path: ${usage}% (threshold: ${threshold}%)"
        return 1
    else
        echo -e "${GREEN}✓${NC} Disk usage at $path: ${usage}%"
        return 0
    fi
}

# 메모리 사용량 확인
check_memory() {
    local threshold=${1:-90}
    local usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    
    if [ $usage -gt $threshold ]; then
        echo -e "${RED}✗${NC} Memory usage: ${usage}% (threshold: ${threshold}%)"
        return 1
    else
        echo -e "${GREEN}✓${NC} Memory usage: ${usage}%"
        return 0
    fi
}

# 포트 확인
check_port() {
    local port=$1
    if ss -tuln | grep -q ":$port "; then
        echo -e "${GREEN}✓${NC} Port $port is listening"
        return 0
    else
        echo -e "${RED}✗${NC} Port $port is not listening"
        return 1
    fi
}

# API 엔드포인트 확인
check_api() {
    local url=$1
    local response=$(curl -s -o /dev/null -w "%{http_code}" $url)
    
    if [ $response -eq 200 ]; then
        echo -e "${GREEN}✓${NC} API endpoint $url is responding (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗${NC} API endpoint $url is not responding (HTTP $response)"
        return 1
    fi
}

# 로그 에러 확인
check_logs() {
    local service=$1
    local minutes=${2:-5}
    local errors=$(journalctl -u $service --since "${minutes} minutes ago" | grep -i "error\|critical\|fatal" | wc -l)
    
    if [ $errors -gt 0 ]; then
        echo -e "${YELLOW}⚠${NC} $service has $errors error(s) in the last $minutes minutes"
        return 1
    else
        echo -e "${GREEN}✓${NC} No errors in $service logs (last $minutes minutes)"
        return 0
    fi
}

# 메인 모니터링 함수
monitor() {
    echo "Security Camera System Health Check"
    echo "=================================="
    echo
    
    # 서비스 상태
    echo "Services:"
    check_service "security-camera.service"
    check_service "nginx"
    echo
    
    # 포트 확인
    echo "Ports:"
    check_port 80
    check_port 443
    check_port 5000
    echo
    
    # API 엔드포인트 확인
    echo "API Endpoints:"
    check_api "http://localhost/health"
    check_api "http://localhost/status"
    echo
    
    # 시스템 리소스
    echo "System Resources:"
    check_memory 85
    check_disk_usage "/" 80
    check_disk_usage "/opt/app" 90
    echo
    
    # 로그 확인
    echo "Recent Logs:"
    check_logs "security-camera.service" 10
    check_logs "nginx" 10
    echo
    
    # 추가 정보
    echo "Additional Info:"
    echo "Uptime: $(uptime -p)"
    echo "Load Average: $(uptime | awk -F'load average:' '{print $2}')"
    echo "Active Connections: $(ss -tuln | wc -l)"
    
    # 데이터베이스 정보
    if [ -f "/opt/app/incidents.db" ]; then
        local db_size=$(du -h /opt/app/incidents.db | awk '{print $1}')
        local incident_count=$(sqlite3 /opt/app/incidents.db "SELECT COUNT(*) FROM incidents;" 2>/dev/null || echo "N/A")
        echo "Database Size: $db_size"
        echo "Total Incidents: $incident_count"
    fi
    
    # 영상 디렉토리 정보
    if [ -d "/opt/app/incident_videos" ]; then
        local video_count=$(find /opt/app/incident_videos -name "*.avi" | wc -l)
        local video_size=$(du -sh /opt/app/incident_videos 2>/dev/null | awk '{print $1}' || echo "N/A")
        echo "Video Files: $video_count"
        echo "Videos Size: $video_size"
    fi
}

# 자동 복구 시도
auto_recovery() {
    echo "Attempting automatic recovery..."
    
    # security-camera 서비스가 중지되어 있으면 재시작
    if ! systemctl is-active --quiet security-camera.service; then
        echo "Restarting security-camera service..."
        sudo systemctl restart security-camera.service
        sleep 5
    fi
    
    # nginx가 중지되어 있으면 재시작
    if ! systemctl is-active --quiet nginx; then
        echo "Restarting nginx..."
        sudo systemctl restart nginx
        sleep 5
    fi
    
    echo "Recovery attempt completed"
}

# 사용법
case "$1" in
    monitor)
        monitor
        ;;
    recovery)
        auto_recovery
        monitor
        ;;
    continuous)
        while true; do
            clear
            monitor
            echo
            echo "Next check in 30 seconds... (Ctrl+C to stop)"
            sleep 30
        done
        ;;
    *)
        echo "Usage: $0 {monitor|recovery|continuous}"
        echo "  monitor    : Run single health check"
        echo "  recovery   : Attempt auto-recovery then check"
        echo "  continuous : Continuous monitoring (30s interval)"
        exit 1
        ;;
esac