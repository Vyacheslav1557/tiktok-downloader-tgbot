from typing import Optional

from api.errors import FileTooLargeError
from api.models import Video
from api.yt_dlp_client import download_video


class YouTubeApiClient:
    def get_content(self, youtube_url: str, max_video_size: Optional[int] = None) -> Video:
        try:
            return download_video(
                youtube_url,
                max_video_size=max_video_size,
                extractor_args={
                    'youtube': {
                        'player_client': ['android', 'ios', 'tv_simply', 'web'],
                    }
                },
            )
        except FileTooLargeError:
            raise
        except Exception as e:
            raise Exception(f"Failed to download YouTube Shorts: {str(e)}") from e
