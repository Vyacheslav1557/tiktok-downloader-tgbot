import os
import tempfile

import requests

from api.models import Collection, Video, Image, Audio, TempFile

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


class TikTokApiClient:
    def __init__(self):
        self.api_url = "https://tikwm.com/api/"

    def get_content(self, tiktok_url: str) -> Collection | Video:
        params = {"url": tiktok_url}

        response = requests.get(self.api_url, params=params, headers=headers)
        response.raise_for_status()
        body = response.json()

        if body.get("code") != 0:
            raise Exception(body.get("msg", "api code error"))

        data = body['data']

        if 'images' in data:
            images = []
            for image_url in data['images']:
                images.append(Image(image_url, save_media_to_tmp(image_url, ".jpg")))

            audio = None
            if 'music_info' in data:
                title = data['music_info']['title']
                audio_url = data['music_info']['play']
                audio = Audio(audio_url, title, save_media_to_tmp(audio_url, ".mp3"))

            return Collection(images, audio)

        elif 'play' in data:
            video_url = data['play']
            # Extract video metadata if available
            width = data.get('width')
            height = data.get('height')
            duration = data.get('duration')
            
            return Video(
                video_url, 
                save_media_to_tmp(video_url, ".mp4"),
                width=width,
                height=height,
                duration=duration
            )

        raise Exception(body.get("msg", "api code error"))


def save_media_to_tmp(url: str, suffix: str) -> TempFile:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file_path = temp_file.name

    response = requests.get(url, headers=headers, stream=True, timeout=30)
    response.raise_for_status()

    with open(temp_file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    file_size = os.path.getsize(temp_file_path)

    return TempFile(file_size, temp_file_path)
