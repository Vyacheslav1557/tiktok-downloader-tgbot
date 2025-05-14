import os
import tempfile

import yt_dlp

from api.models import TempFile, Video


class YouTubeApiClient:
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestvideo[vcodec~="^h264$"][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True
        }

    def get_content(self, youtube_url: str) -> Video:
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)  # Download the video
                video_path = ydl.prepare_filename(info)  # Get the path to the downloaded file
                file_size = os.path.getsize(video_path)
                return Video(youtube_url, TempFile(file_size, video_path))
        except Exception as e:
            raise Exception(f"Failed to download YouTube Shorts: {str(e)}")
