import html
import random
import re
from typing import Callable, Optional

import telegram
from telegram import BotCommand, InputMediaPhoto, Update
from telegram.ext import Application, ContextTypes

from api import Collection, FileTooLargeError, InstagramApiClient, TikTokApiClient, Video, YouTubeApiClient
from logger import logger

tiktok_api_client = TikTokApiClient()
youtube_api_client = YouTubeApiClient()
instagram_api_client = InstagramApiClient()

TELEGRAM_MAX_IMG_SIZE = 10 * 1024 * 1024
TELEGRAM_MAX_VIDEO_SIZE = 50 * 1024 * 1024

TIKTOK_LINK_RE = re.compile(r"https?://(www\.)?(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)/.+")
YOUTUBE_SHORTS_LINK_RE = re.compile(r"https?://(www\.)?youtube\.com/shorts/.+|https?://youtu\.be/.+")
INSTAGRAM_REELS_LINK_RE = re.compile(r"https?://(www\.)?instagram\.com/(reels?|p)/.+")

ContentGetter = Callable[[str, Optional[int]], Collection | Video]


def is_tiktok_link(text: str) -> bool:
    return bool(TIKTOK_LINK_RE.match(text))


def is_youtube_shorts_link(text: str) -> bool:
    return bool(YOUTUBE_SHORTS_LINK_RE.match(text))


def is_instagram_reels_link(text: str) -> bool:
    return bool(INSTAGRAM_REELS_LINK_RE.match(text))


def detect_content_getter(url: str) -> Optional[ContentGetter]:
    if is_tiktok_link(url):
        return tiktok_api_client.get_content
    if is_youtube_shorts_link(url):
        return youtube_api_client.get_content
    if is_instagram_reels_link(url):
        return instagram_api_client.get_content
    return None


def build_caption(user: telegram.User, url: str) -> str:
    user_name = html.escape(user.username or user.first_name)
    user_link = f'<a href="tg://user?id={user.id}">{user_name}</a>'
    original_link = f'<a href="{html.escape(url, quote=True)}">оригинал</a>'
    return f"От {user_link} - {original_link}"


async def send_too_large_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, url: str) -> None:
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Видео слишком большое. <a href=\"{html.escape(url, quote=True)}\">Оригинал</a>.",
        parse_mode=telegram.constants.ParseMode.HTML,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    url = message.text.strip()
    get_content = detect_content_getter(url)
    if not get_content:
        return

    chat_id = message.chat_id
    caption = build_caption(message.from_user, url)

    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message: {e}")

    try:
        content = get_content(url, TELEGRAM_MAX_VIDEO_SIZE)

        if isinstance(content, Collection):
            with content as collection:
                media_group = []
                for image in collection.images[:10]:
                    if not image.temp or image.temp.size > TELEGRAM_MAX_IMG_SIZE:
                        continue

                    with open(image.temp.path, "rb") as image_file:
                        media_group.append(InputMediaPhoto(media=image_file.read()))

                if not media_group:
                    raise Exception("No images to send")

                media_group[0].caption = caption
                media_group[0].parse_mode = telegram.constants.ParseMode.HTML
                await context.bot.send_media_group(chat_id=chat_id, media=media_group)
                logger.info("Images sent successfully as media group")

                if collection.audio and collection.audio.temp:
                    with open(collection.audio.temp.path, "rb") as audio_file:
                        audio_data = audio_file.read()

                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio_data,
                        title=collection.audio.title,
                        caption=caption,
                        parse_mode=telegram.constants.ParseMode.HTML,
                    )
                    logger.info("Audio sent successfully")

            return

        if isinstance(content, Video):
            with content as video:
                if not video.temp:
                    raise Exception("No video to send")

                if video.temp.size > TELEGRAM_MAX_VIDEO_SIZE:
                    await send_too_large_message(context, chat_id, url)
                    return

                with open(video.temp.path, "rb") as video_file:
                    video_data = video_file.read()

                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_data,
                    supports_streaming=True,
                    caption=caption,
                    parse_mode=telegram.constants.ParseMode.HTML,
                    width=video.width,
                    height=video.height,
                    duration=video.duration,
                )
                logger.info("Video sent successfully")
            return

        raise Exception("Unsupported content type")

    except FileTooLargeError as e:
        logger.info(f"Video is too large to send: size={e.size}, limit={e.limit}, url={url}")
        await send_too_large_message(context, chat_id, url)
    except Exception as e:
        logger.error(f"Error sending content: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Что-то пошло не так. <a href=\"{html.escape(url, quote=True)}\">Оригинал</a>.",
            parse_mode=telegram.constants.ParseMode.HTML,
        )


async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    min_value = 100_000
    max_value = 1_000_000 - 1

    try:
        if len(context.args) == 1:
            min_value = 1
            max_value = int(context.args[0])
        elif len(context.args) == 2:
            min_value = int(context.args[0])
            max_value = int(context.args[1])

        await message.reply_text(str(random.randint(min_value, max_value)))
    except ValueError:
        await context.bot.send_message(chat_id=message.chat_id, text="Хочу чиселки!")
    except Exception as e:
        logger.error(f"Error rolling: {e}")
        await context.bot.send_message(
            chat_id=message.chat_id,
            text="Что-то пошло не так. Попробуйте позже.",
        )


async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    if len(context.args) <= 1:
        await context.bot.send_message(chat_id=message.chat_id, text="А где выбор?")
        return

    await context.bot.send_message(chat_id=message.chat_id, text=random.choice(context.args))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    help_text = (
        "<b>Доступные команды:</b>\n\n"
        "🎲 <code>/roll [max]</code> или <code>/roll [min] [max]</code>\n"
        "Случайное число от 1 до 1,000,000 по умолчанию\n\n"
        "🤔 <code>/ch option1 option2 ...</code>\n"
        "Выбрать одну опцию из предложенных\n\n"
        "💬 <code>/help</code>\n"
        "Показать это сообщение\n\n"
        "📹 <b>Автоматическая обработка:</b>\n"
        "Отправь ссылку на TikTok, YouTube Shorts или Instagram Reels, и я скачаю видео/фото"
    )

    await context.bot.send_message(
        chat_id=message.chat_id,
        text=help_text,
        parse_mode=telegram.constants.ParseMode.HTML,
    )


async def set_commands(app: Application) -> None:
    commands = [
        BotCommand("roll", "Случайное число"),
        BotCommand("ch", "Выбрать из опций"),
        BotCommand("help", "Справка по командам"),
    ]
    await app.bot.set_my_commands(commands)
