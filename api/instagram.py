import os
import tempfile

import yt_dlp

from api.models import TempFile, Video

YDL_OPTS = {
    'format': 'best[ext=mp4][vcodec^=avc1][acodec!=none]/best[ext=mp4][acodec!=none]/best[acodec!=none]/best',
    'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s.%(ext)s'),
    'noplaylist': True,
    'quiet': True,
}


class InstagramApiClient:
    def get_content(self, instagram_url: str) -> Video:
        try:
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(instagram_url, download=True)  # Download the video
                video_path = ydl.prepare_filename(info)  # Get the path to the downloaded file
                file_size = os.path.getsize(video_path)
                return Video(instagram_url, TempFile(file_size, video_path))
        except Exception as e:
            raise Exception(f"Failed to download Instagram Reel: {str(e)}")

