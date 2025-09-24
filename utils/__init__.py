import functools

# 기존 TryExcept 클래스 유지
class TryExcept:
    """YOLOv5 호환용 TryExcept 클래스"""
    def __init__(self, msg=''):
        self.msg = msg

    def __call__(self, func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f'ERROR: {func.__name__}: {e}')
                return None
        return handler

emojis = ''

# helpers.py에서 필요한 함수들을 import
from .helpers import build_media_url, utc_iso_now, paginate_query
