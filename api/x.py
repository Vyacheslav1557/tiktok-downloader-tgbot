import os
import re
import tempfile
from datetime import datetime
from typing import Any, Optional, cast

import requests
import yt_dlp

from api.errors import FileTooLargeError
from api.models import Image, Post, TempFile, Video
from api.x_card import render_x_post_card

REQUEST_TIMEOUT = 30
PRECHECK_TIMEOUT = 15
X_STATUS_ID_RE = re.compile(r"(?:x|twitter)\.com/[^\s]+/status/(\d+)")
TCO_LINK_RE = re.compile(r"https?://t\.co/\S+")


def _extract_status_id(post_url: str) -> str:
    match = X_STATUS_ID_RE.search(post_url)
    if not match:
        raise Exception("Invalid X/Twitter post URL")
    return match.group(1)


def _first_text(data: Any, keys: list[str]) -> Optional[str]:
    if not isinstance(data, dict):
        return None

    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _sanitize_post_text(text: Optional[str]) -> str:
    if not text:
        return ""

    cleaned = TCO_LINK_RE.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _extract_metadata(status: dict[str, Any]) -> tuple[str, str, str, Optional[str], Optional[str]]:
    user = status.get("user") if isinstance(status.get("user"), dict) else {}
    author_name = _first_text(user, ["name", "screen_name"]) or "Unknown"
    handle_raw = _first_text(user, ["screen_name"]) or "unknown"
    handle = handle_raw if handle_raw.startswith("@") else f"@{handle_raw}"
    post_text = _sanitize_post_text(_first_text(status, ["full_text", "text"]))

    quote_text = None
    quoted = status.get("quoted_status")
    if isinstance(quoted, dict):
        quote_text = _sanitize_post_text(_first_text(quoted, ["full_text", "text"]))

    reply_to = _first_text(status, ["in_reply_to_screen_name"])
    if reply_to and not reply_to.startswith("@"):
        reply_to = f"@{reply_to}"

    return author_name, handle, post_text, quote_text, reply_to


def _extract_avatar_url(status: dict[str, Any]) -> Optional[str]:
    user = status.get("user")
    if not isinstance(user, dict):
        return None

    avatar = user.get("profile_image_url_https") or user.get("profile_image_url")
    if not isinstance(avatar, str):
        return None

    return avatar.replace("_normal", "_400x400")


def _format_published_at(status: dict[str, Any]) -> Optional[str]:
    created_at = status.get("created_at")
    if not isinstance(created_at, str) or not created_at.strip():
        return None

    try:
        parsed = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
    except ValueError:
        return None

    return parsed.strftime("%I:%M %p · %b %d, %Y").lstrip("0")


def _extract_views_count(twitter_ie: Any, status_id: str) -> Optional[int]:
    try:
        raw = twitter_ie._call_graphql_api(twitter_ie._GRAPHQL_ENDPOINT, status_id)
    except Exception:
        return None

    if not isinstance(raw, dict):
        return None

    tweet_result = raw.get("tweetResult")
    if not isinstance(tweet_result, dict):
        return None

    result = tweet_result.get("result")
    if not isinstance(result, dict):
        return None

    views = result.get("views")
    if not isinstance(views, dict):
        return None

    count_value = views.get("count")
    if isinstance(count_value, str) and count_value.isdigit():
        return int(count_value)
    if isinstance(count_value, int):
        return count_value
    return None


def _format_views(count: Optional[int]) -> Optional[str]:
    if count is None:
        return None

    if count < 1000:
        return f"{count} views"
    if count < 1_000_000:
        return f"{count / 1000:.1f}K views".replace(".0K", "K")
    return f"{count / 1_000_000:.1f}M views".replace(".0M", "M")


def _extract_media_items(status: dict[str, Any]) -> list[dict[str, Any]]:
    extended_entities = status.get("extended_entities")
    if not isinstance(extended_entities, dict):
        return []

    media = extended_entities.get("media")
    if not isinstance(media, list):
        return []

    return [item for item in media if isinstance(item, dict)]


def _pick_variant_url(media_item: dict[str, Any]) -> Optional[str]:
    video_info = media_item.get("video_info")
    if not isinstance(video_info, dict):
        return None

    variants = video_info.get("variants")
    if not isinstance(variants, list):
        return None

    mp4_variants = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue

        url = variant.get("url")
        if not isinstance(url, str) or not url.startswith("http"):
            continue

        content_type = variant.get("content_type")
        if content_type != "video/mp4":
            continue

        mp4_variants.append(variant)

    if not mp4_variants:
        return None

    mp4_variants.sort(key=lambda item: -(item.get("bitrate") or 0))
    return mp4_variants[0].get("url")


def _extract_dimensions(media_item: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    original_info = media_item.get("original_info")
    if isinstance(original_info, dict):
        width = original_info.get("width")
        height = original_info.get("height")
        if isinstance(width, int) and isinstance(height, int):
            return width, height

    sizes = media_item.get("sizes")
    if isinstance(sizes, dict):
        for key in ("large", "medium", "small", "thumb"):
            size = sizes.get(key)
            if not isinstance(size, dict):
                continue
            width = size.get("w")
            height = size.get("h")
            if isinstance(width, int) and isinstance(height, int):
                return width, height

    return None, None


def _download_to_temp(url: str, suffix: str, max_size: Optional[int]) -> TempFile:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name

    try:
        with requests.head(url, allow_redirects=True, timeout=PRECHECK_TIMEOUT) as head_response:
            head_response.raise_for_status()
            content_length = head_response.headers.get("Content-Length")
            if max_size is not None and content_length and content_length.isdigit() and int(content_length) > max_size:
                raise FileTooLargeError(int(content_length), max_size)
    except requests.RequestException:
        pass

    size = 0
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            with open(temp_path, "wb") as file_handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue

                    size += len(chunk)
                    if max_size is not None and size > max_size:
                        raise FileTooLargeError(size, max_size)
                    file_handle.write(chunk)
    except Exception:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass
        raise

    return TempFile(size=size, path=temp_path)


class XApiClient:
    def get_content(
        self,
        post_url: str,
        max_video_size: Optional[int] = None,
        max_image_size: Optional[int] = None,
    ) -> Post:
        status_id = _extract_status_id(post_url)
        ydl_opts: dict[str, Any] = {"quiet": True}

        ydl_factory = cast(Any, yt_dlp.YoutubeDL)
        with ydl_factory(ydl_opts) as ydl:
            twitter_ie = ydl.get_info_extractor("Twitter")
            status = cast(Any, getattr(twitter_ie, "_extract_status"))(status_id)
            views_count = _extract_views_count(twitter_ie, status_id)

        if not isinstance(status, dict) or not status:
            raise Exception("Failed to fetch X/Twitter post metadata")

        author_name, handle, post_text, quote_text, reply_to = _extract_metadata(status)
        avatar_url = _extract_avatar_url(status)
        published_at_text = _format_published_at(status)
        views_text = _format_views(views_count)
        media: list[Image | Video] = []
        for media_item in _extract_media_items(status):
            media_type = media_item.get("type")

            if media_type == "photo":
                media_url = media_item.get("media_url_https") or media_item.get("media_url")
                if not isinstance(media_url, str):
                    continue
                if "?" not in media_url:
                    media_url = f"{media_url}?name=orig"

                try:
                    image_temp = _download_to_temp(media_url, ".jpg", max_image_size)
                    media.append(Image(url=media_url, temp=image_temp))
                except FileTooLargeError:
                    continue
                continue

            if media_type in {"video", "animated_gif"}:
                video_url = _pick_variant_url(media_item)
                if not video_url:
                    continue

                width, height = _extract_dimensions(media_item)
                duration_millis = None
                video_info = media_item.get("video_info")
                if isinstance(video_info, dict):
                    duration_millis = video_info.get("duration_millis")
                duration = int(duration_millis / 1000) if isinstance(duration_millis, int) else None

                try:
                    video_temp = _download_to_temp(video_url, ".mp4", max_video_size)
                    media.append(Video(url=video_url, temp=video_temp, width=width, height=height, duration=duration))
                except FileTooLargeError:
                    continue

        inline_image_path = None
        inlined_image_url = None
        image_media = [item for item in media if isinstance(item, Image)]
        video_media = [item for item in media if isinstance(item, Video)]
        if len(image_media) == 1 and not video_media:
            first_image = image_media[0]
            if first_image.temp:
                inline_image_path = first_image.temp.path
                inlined_image_url = first_image.url

        avatar_path = None
        if avatar_url:
            try:
                avatar_temp = _download_to_temp(avatar_url, ".jpg", max_size=2 * 1024 * 1024)
                avatar_path = avatar_temp.path
            except Exception:
                avatar_path = None

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as card_file:
            card_path = card_file.name

        try:
            render_x_post_card(
                output_path=card_path,
                author_name=author_name,
                handle=handle,
                post_text=post_text,
                quote_text=quote_text,
                reply_to_text=reply_to,
                inline_image_path=inline_image_path,
                avatar_image_path=avatar_path,
                published_at_text=published_at_text,
                views_text=views_text,
            )
        finally:
            if avatar_path:
                try:
                    os.remove(avatar_path)
                except FileNotFoundError:
                    pass

        card_size = os.path.getsize(card_path)
        card = Image(url=post_url, temp=TempFile(size=card_size, path=card_path))

        return Post(card=card, media=media, inlined_image_url=inlined_image_url)
