import os
from typing import Optional

from api.errors import FileTooLargeError
from api.models import Video
from api.yt_dlp_client import download_video


class InstagramApiClient:
    def get_content(self, instagram_url: str, max_video_size: Optional[int] = None) -> Video:
        # Instagram отдаёт пустой ответ для неавторизованных запросов, поэтому
        # yt-dlp нужны cookies залогиненного аккаунта. Путь к cookies.txt берём
        # из переменной окружения INSTAGRAM_COOKIES (если задана).
        cookiefile = os.getenv("INSTAGRAM_COOKIES") or None
        try:
            return download_video(instagram_url, max_video_size=max_video_size, cookiefile=cookiefile)
        except FileTooLargeError:
            raise
        except Exception as e:
            raise Exception(f"Failed to download Instagram Reel: {str(e)}") from e
