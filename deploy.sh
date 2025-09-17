#!/bin/bash
# EC2 Ubuntu 서버 배포 스크립트

set -e  # 오류 발생 시 스크립트 중단

echo "Security Camera Backend 배포 시작..."

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필요한 패키지 설치
sudo apt install -y python3 python3-pip python3-venv nginx supervisor
sudo apt install -y libopencv-dev python3-opencv
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

# 애플리케이션 디렉토리 생성
sudo mkdir -p /opt/app
sudo mkdir -p /opt/app/incident_videos
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/run/gunicorn

# 소유권 설정
sudo chown -R www-data:www-data /opt/app
sudo chown -R www-data:www-data /var/log/gunicorn
sudo chown -R www-data:www-data /var/run/gunicorn

# 애플리케이션 파일 복사 (실제 배포시에는 git clone 또는 파일 업로드)
# sudo cp app.py /opt/app/
# sudo cp requirements.txt /opt/app/
# sudo cp gunicorn_config.py /opt/app/

# 가상환경 생성
cd /opt/app
sudo -u www-data python3 -m venv venv
sudo -u www-data /opt/app/venv/bin/pip install --upgrade pip

# 패키지 설치
sudo -u www-data /opt/app/venv/bin/pip install -r requirements.txt
sudo -u www-data /opt/app/venv/bin/pip install gunicorn

# 환경 변수 설정
sudo tee /opt/app/.env << EOF
FLASK_ENV=production
UPLOAD_FOLDER=/opt/app/incident_videos
DATABASE_PATH=/opt/app/incidents.db
SECRET_KEY=$(openssl rand -hex 32)
PORT=5000
EOF

# 소유권 설정
sudo chown www-data:www-data /opt/app/.env

# systemd 서비스 파일 복사
sudo cp security-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable security-camera.service

# nginx 설정
sudo cp nginx.conf /etc/nginx/sites-available/security-camera
sudo ln -sf /etc/nginx/sites-available/security-camera /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# nginx 설정 테스트
sudo nginx -t

# 방화벽 설정
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh

# 로그 디렉토리 권한 설정
sudo mkdir -p /var/log/nginx
sudo chown -R www-data:adm /var/log/nginx

# 서비스 시작
sudo systemctl start security-camera.service
sudo systemctl restart nginx

# 서비스 상태 확인
sudo systemctl status security-camera.service
sudo systemctl status nginx

echo "배포 완료!"
echo "서비스 상태 확인: sudo systemctl status security-camera"
echo "로그 확인: sudo journalctl -u security-camera -f"
echo "nginx 로그: sudo tail -f /var/log/nginx/security_camera_error.log"