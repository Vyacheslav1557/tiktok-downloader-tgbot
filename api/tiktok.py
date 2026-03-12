import os
import re
import tempfile
from typing import Optional

import requests

from api.errors import FileTooLargeError
from api.models import Collection, Video, Image, Audio, TempFile

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

REQUEST_TIMEOUT = 30
PRECHECK_TIMEOUT = 15


class TikTokApiClient:
    def __init__(self):
        self.api_url = "https://tikwm.com/api/"

    def get_content(self, tiktok_url: str, max_video_size: Optional[int] = None) -> Collection | Video:
        params = {"url": tiktok_url}

        response = requests.get(self.api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
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
            width = data.get('width')
            height = data.get('height')
            duration = data.get('duration')
            
            return Video(
                video_url, 
                save_media_to_tmp(video_url, ".mp4", max_size=max_video_size),
                width=width,
                height=height,
                duration=duration
            )

        raise Exception(body.get("msg", "api code error"))


def _parse_content_length(value: Optional[str]) -> Optional[int]:
    if not value:
        return None

    try:
        content_length = int(value)
        if content_length > 0:
            return content_length
    except ValueError:
        return None

    return None


def _get_remote_file_size(url: str) -> Optional[int]:
    try:
        with requests.head(url, headers=headers, allow_redirects=True, timeout=PRECHECK_TIMEOUT) as head_response:
            head_response.raise_for_status()
            head_size = _parse_content_length(head_response.headers.get('Content-Length'))
            if head_size is not None:
                return head_size
    except requests.RequestException:
        pass

    try:
        range_headers = dict(headers)
        range_headers['Range'] = 'bytes=0-0'
        with requests.get(url, headers=range_headers, stream=True, timeout=PRECHECK_TIMEOUT) as range_response:
            range_response.raise_for_status()

            content_range = range_response.headers.get('Content-Range')
            if content_range:
                match = re.search(r'/([0-9]+)$', content_range)
                if match:
                    return int(match.group(1))

            range_size = _parse_content_length(range_response.headers.get('Content-Length'))
            if range_size is not None:
                return range_size
    except requests.RequestException:
        return None

    return None


def _remove_temp_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        return


def _download_to_temp_file(url: str, temp_file_path: str, max_size: Optional[int]) -> int:
    downloaded_size = 0
    try:
        with requests.get(url, headers=headers, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()

            with open(temp_file_path, "wb") as file_handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue

                    downloaded_size += len(chunk)
                    if max_size is not None and downloaded_size > max_size:
                        raise FileTooLargeError(downloaded_size, max_size)

                    file_handle.write(chunk)

        return downloaded_size
    except Exception:
        _remove_temp_file(temp_file_path)
        raise


def save_media_to_tmp(url: str, suffix: str, max_size: Optional[int] = None) -> TempFile:
    remote_file_size = _get_remote_file_size(url)
    if max_size is not None and remote_file_size is not None and remote_file_size > max_size:
        raise FileTooLargeError(remote_file_size, max_size)

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file_path = temp_file.name

    file_size = _download_to_temp_file(url, temp_file_path, max_size=max_size)
    if max_size is not None and file_size > max_size:
        _remove_temp_file(temp_file_path)
        raise FileTooLargeError(file_size, max_size)

    return TempFile(file_size, temp_file_path)
