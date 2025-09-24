import os
from urllib.parse import urlparse
import boto3
from botocore.config import Config as BotoCfg
from botocore.exceptions import ClientError, NoCredentialsError
from flask import Blueprint, request

from sf_models.entities import db, Event
from utils.helpers import build_media_url
from services.auth_service import authed

s3_bp = Blueprint("s3", __name__)

def _normalize_bucket(b: str | None) -> str | None:
    if not b:
        return b
    b = b.strip()
    if b.startswith(("http://", "https://")):
        host = urlparse(b).netloc
        return host.split(".")[0]
    return b

S3_BUCKET = _normalize_bucket(os.getenv("S3_BUCKET", "safefall2"))
S3_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
os.environ["AWS_EC2_METADATA_DISABLED"] = os.getenv("AWS_EC2_METADATA_DISABLED", "false")

BOTO_CFG = BotoCfg(signature_version="s3v4",
                   retries={"max_attempts": 2, "mode": "standard"},
                   connect_timeout=2, read_timeout=3)
_s3 = boto3.client("s3", region_name=S3_REGION, config=BOTO_CFG)

@s3_bp.post("/media/presign")
def media_presign_put():
    if not authed(request):
        return {"code": "UNAUTHORIZED", "message": "invalid token"}, 401

    data = request.get_json(force=True, silent=True) or {}
    key = data.get("key")
    content_type = data.get("content_type", "application/octet-stream")
    if not key:
        return {"code": "BAD_REQUEST", "message": "key required"}, 400

    try:
        url = _s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": S3_BUCKET, "Key": key, "ContentType": content_type},
            ExpiresIn=3600, HttpMethod="PUT",
        )
        return {"url": url, "method": "PUT", "expiresIn": 3600}, 200
    except NoCredentialsError:
        return {"code": "NO_AWS_CREDS", "message": "No AWS credentials available"}, 500
    except ClientError as e:
        return {"code": "S3_ERROR", "message": str(e)}, 500
    except Exception as e:
        return {"code": "INTERNAL", "message": str(e)}, 500

@s3_bp.post("/events/register")
def events_register():
    if not authed(request):
        return {"code": "UNAUTHORIZED", "message": "invalid token"}, 401

    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get("device_id", "unknown")
    key = data.get("key")
    ev_type = data.get("type", "fall")
    if not key:
        return {"code": "BAD_REQUEST", "message": "key required"}, 400

    evt = Event(device_id=device_id, path=key, type=ev_type)
    db.session.add(evt); db.session.commit()

    return {
        "ok": True,
        "event": {
            "id": evt.id, "device_id": evt.device_id,
            "t_event": evt.t_event.isoformat() if evt.t_event else None,
            "path": evt.path, "type": evt.type,
            "url": build_media_url(evt.path, S3_BUCKET, S3_REGION),
        }
    }, 200
