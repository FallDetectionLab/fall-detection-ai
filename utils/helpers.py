import os
from datetime import datetime

S3_BUCKET = os.getenv("S3_BUCKET", "safefall2")
S3_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
MEDIA_ROOT = os.getenv("MEDIA_ROOT", "./media")

def utc_iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"

def paginate_query(query, page=1, limit=10):
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "data": items,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1
        }
    }

def build_media_url(path: str | None, s3_bucket: str | None = None, s3_region: str | None = None) -> str | None:
    if not path:
        return None
    local_full = os.path.join(MEDIA_ROOT, path)
    if os.path.exists(local_full):
        return f"/api/v1/media/{path}"
    b = s3_bucket or S3_BUCKET
    r = s3_region or S3_REGION
    return f"https://{b}.s3.{r}.amazonaws.com/{path}"
