import os
import tempfile
from typing import Any, Optional, cast

import yt_dlp

from api.errors import FileTooLargeError
from api.models import TempFile, Video

BASE_YDL_OPTS: dict[str, Any] = {
    'format': 'bv*+ba/b',
    'merge_output_format': 'mp4',
    'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s.%(ext)s'),
    'noplaylist': True,
    'quiet': True,
}


def _resolve_downloaded_path(info: Any, ydl: yt_dlp.YoutubeDL) -> str:
    requested_downloads = info.get('requested_downloads') or []
    if requested_downloads:
        file_path = requested_downloads[0].get('filepath')
        if file_path and os.path.exists(file_path):
            return file_path

    file_path = info.get('_filename')
    if file_path and os.path.exists(file_path):
        return file_path

    file_path = ydl.prepare_filename(info)
    if file_path and os.path.exists(file_path):
        return file_path

    raise FileNotFoundError('Downloaded file was not found on disk')


def _extract_size_from_format(format_info: Any) -> Optional[int]:
    if not isinstance(format_info, dict):
        return None

    for key in ('filesize', 'filesize_approx'):
        value = format_info.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return int(value)

    return None


def _estimate_video_size(info: Any) -> Optional[int]:
    if not isinstance(info, dict):
        return None

    requested_formats = info.get('requested_formats') or []
    if requested_formats:
        total_size = 0
        for format_info in requested_formats:
            format_size = _extract_size_from_format(format_info)
            if format_size is None:
                total_size = 0
                break
            total_size += format_size

        if total_size > 0:
            return total_size

    for candidate in (info.get('requested_format'), info):
        size = _extract_size_from_format(candidate)
        if size is not None:
            return size

    return None


def _build_ydl_options(max_video_size: Optional[int], extractor_args: Optional[dict[str, Any]]) -> dict[str, Any]:
    ydl_options = dict(BASE_YDL_OPTS)
    if max_video_size is not None:
        ydl_options['max_filesize'] = max_video_size
    if extractor_args:
        ydl_options['extractor_args'] = extractor_args
    return ydl_options


def download_video(url: str, max_video_size: Optional[int] = None, extractor_args: Optional[dict[str, Any]] = None) -> Video:
    ydl_options = _build_ydl_options(max_video_size, extractor_args)

    with yt_dlp.YoutubeDL(cast(Any, ydl_options)) as ydl:
        preflight_info = ydl.extract_info(url, download=False)
        estimated_size = _estimate_video_size(preflight_info)
        if max_video_size is not None and estimated_size is not None and estimated_size > max_video_size:
            raise FileTooLargeError(estimated_size, max_video_size)

        info = ydl.extract_info(url, download=True)
        video_path = _resolve_downloaded_path(info, ydl)
        file_size = os.path.getsize(video_path)
        if file_size == 0:
            raise Exception('Downloaded file is empty')
        if max_video_size is not None and file_size > max_video_size:
            raise FileTooLargeError(file_size, max_video_size)

        return Video(
            url,
            TempFile(file_size, video_path),
            width=info.get('width'),
            height=info.get('height'),
            duration=info.get('duration'),
        )
