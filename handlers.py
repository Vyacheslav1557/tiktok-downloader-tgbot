import asyncio
import random
import re
import html

import telegram
from telegram import Update, InputMediaPhoto, BotCommand
from telegram.ext import ContextTypes, Application

from api import TikTokApiClient, Collection, Video, YouTubeApiClient, InstagramApiClient
from logger import logger

tiktokApiClient = TikTokApiClient()
youtubeApiClient = YouTubeApiClient()
instagramApiClient = InstagramApiClient()


def is_tiktok_link(text: str) -> bool:
    tiktok_pattern = r"(https?://(www\.)?(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)/.+)"
    return bool(re.match(tiktok_pattern, text))


def is_youtube_shorts_link(text: str) -> bool:
    shorts_pattern = r"(https?://(www\.)?youtube\.com/shorts/.+|https?://youtu\.be/.+)"
    return bool(re.match(shorts_pattern, text))


def is_instagram_reels_link(text: str) -> bool:
    instagram_pattern = r"(https?://(www\.)?instagram\.com/(reels?|p)/.+)"
    return bool(re.match(instagram_pattern, text))


def build_caption(user: telegram.User, url: str) -> str:
    user_id = user.id
    username = html.escape(user.username or user.first_name)
    user_link = f'<a href="tg://user?id={user_id}">{username}</a>'

    original = f'<a href="{url}">оригинал</a>'

    return f"От {user_link} - {original}"


TELEGRAM_MAX_IMG_SIZE = 10 * 1024 * 1024
TELEGRAM_MAX_VIDEO_SIZE = 50 * 1024 * 1024

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    message = update.message
    url = message.text
    chat_id = message.chat_id
    caption = build_caption(message.from_user, url)

    if not is_tiktok_link(url) and not is_youtube_shorts_link(url) and not is_instagram_reels_link(url):
        return

    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    try:
        content = None
        
        if is_tiktok_link(url):
            content = tiktokApiClient.get_content(url)
        elif is_youtube_shorts_link(url):
            content = youtubeApiClient.get_content(url)
        elif is_instagram_reels_link(url):
            content = instagramApiClient.get_content(url)

        if isinstance(content, Collection):
            with content as collection:
                media_group = []
                for img in collection.images[:10]:
                    if img.temp.size > TELEGRAM_MAX_IMG_SIZE:
                        continue

                    with open(img.temp.path, "rb") as image_file:
                        media_group.append(InputMediaPhoto(media=image_file.read()))

                if media_group:
                    await context.bot.send_media_group(
                        chat_id=chat_id,
                        media=media_group,
                        caption=caption,
                        parse_mode=telegram.constants.ParseMode.HTML
                    )
                    logger.info("Images sent successfully as media group")
                else:
                    logger.warning("No images to send")
                    raise Exception("No images to send")

                if collection.audio:
                    with open(collection.audio.temp.path, "rb") as audio_file:
                        audio_data = audio_file.read()
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio_data,
                        title=collection.audio.title,
                        caption=caption,
                        parse_mode=telegram.constants.ParseMode.HTML
                    )
                    logger.info("Audio sent successfully as audio")

        elif isinstance(content, Video):
            with content as video:
                if video.temp.size > TELEGRAM_MAX_VIDEO_SIZE:
                    await context.bot.send_message(
                        update.message.chat_id, 
                        f"Видео слишком большое. <a href=\"{url}\">Оригинал</a>.",
                        parse_mode=telegram.constants.ParseMode.HTML
                    )
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
                    duration=video.duration
                )
                logger.info("Video sent successfully as media")

    except Exception as e:
        logger.error(f"Error sending content: {e}")
        await context.bot.send_message(
            update.message.chat_id,
            f"Что-то пошло не так. <a href=\"{url}\">Оригинал</a>.",
            parse_mode=telegram.constants.ParseMode.HTML
        )


async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    a = 100_000
    b = 1_000_000 - 1

    try:
        if len(context.args) == 1:
            a = 1
            b = int(context.args[0])
        elif len(context.args) == 2:
            a = int(context.args[0])
            b = int(context.args[1])

        await update.message.reply_text(str(random.randint(a, b)))
    except ValueError as e:
        await context.bot.send_message(update.message.chat_id, "Хочу чиселки!")
        return
    except Exception as e:
        logger.error(f"Error rolling: {e}")
        await context.bot.send_message(
            update.message.chat_id, 
            f"Что-то пошло не так. Попробуйте позже.",
        )
        return


async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) <= 1:
        await context.bot.send_message(update.message.chat_id, "А где выбор?")
        return

    await context.bot.send_message(
        update.message.chat_id,
        random.choice(context.args)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
*Доступные команды:*

🎲 /roll [max] или /roll [min] [max]
   Случайное число от 1 до 1,000,000 по умолчанию

🤔 /ch option1 option2 \.\.\.
   Выбрать одну опцию из предложенных

💬 /help
   Показать это сообщение

📹 *Автоматическая обработка:*
   Просто отправь ссылку на TikTok, YouTube Shorts или Instagram Reels, и я скачаю видео/фото
    """
    await context.bot.send_message(
        update.message.chat_id,
        help_text,
        parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
    )

async def set_commands(self: Application) -> None:
    commands = [
        BotCommand("roll", "Случайное число"),
        BotCommand("ch", "Выбрать из опций"),
        BotCommand("help", "Справка по командам"),
    ]
    await self.bot.set_my_commands(commands)