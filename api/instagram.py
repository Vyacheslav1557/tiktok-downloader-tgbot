from typing import Optional

from api.errors import FileTooLargeError
from api.models import Video
from api.yt_dlp_client import download_video


class InstagramApiClient:
    def get_content(self, instagram_url: str, max_video_size: Optional[int] = None) -> Video:
        try:
            return download_video(instagram_url, max_video_size=max_video_size)
        except FileTooLargeError:
            raise
        except Exception as e:
            raise Exception(f"Failed to download Instagram Reel: {str(e)}") from e
