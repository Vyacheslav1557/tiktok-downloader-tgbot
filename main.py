import os

import dotenv
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
)

from handlers import roll, handle_message, choose, help_command, set_commands
from logger import logger

dotenv.load_dotenv()


def main() -> None:
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("roll", roll))
    app.add_handler(CommandHandler("ch", choose))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.post_init = set_commands

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
