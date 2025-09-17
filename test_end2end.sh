#!/bin/bash
set -e

TOKEN="test-token"
API="http://web-alb-1848254395.ap-northeast-2.elb.amazonaws.com"
DEVICE="pi-01"
KEY="frames/$DEVICE/test-end2end-$(date +%Y%m%d_%H%M%S).jpg"

echo "==> 1. presign 요청..."
RESP=$(curl -s -X POST "$API/media/presign" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"key\":\"$KEY\",\"content_type\":\"image/jpeg\"}")

UPLOAD_URL=$(echo "$RESP" | jq -r .upload_url)
HDR_CT=$(echo "$RESP" | jq -r '.headers["Content-Type"]')

echo "   upload_url=$UPLOAD_URL"
echo "   content-type=$HDR_CT"

echo "==> 2. S3 업로드 (샘플 이미지 대신 /etc/hosts 업로드)"
curl -s -o /dev/null -w "%{http_code}" -X PUT -T /etc/hosts \
  -H "Content-Type: $HDR_CT" \
  "$UPLOAD_URL"
echo "   (↑ 200 나오면 성공)"

echo "==> 3. 이벤트 등록"
curl -s -X POST "$API/events" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
        \"device_id\": \"$DEVICE\",
        \"type\": \"frame\",
        \"media\": [{\"kind\": \"frame\", \"key\": \"$KEY\"}]
      }"

echo
echo "==> 4. 최근 이벤트 목록 확인"
curl -s "$API/events" | jq '.items[0]'
