![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![PyPI - python-telegram-bot](https://img.shields.io/pypi/v/python-telegram-bot?style=flat-square&logo=python&label=python-telegram-bot)](https://pypi.org/project/python-telegram-bot/)

# tiktok-downloader-tgbot

Телеграм-бот для скачивания видео и коллекций (фото + аудио) из TikTok, а также скачивания шортсов из YouTube.

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/Vyacheslav1557/tiktok-downloader-tgbot
cd tiktok-downloader-tgbot
````

### 2\. Установка Poetry (если уже не установлен)

Poetry используется для управления зависимостями проекта.

**Linux / macOS:**

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Windows (PowerShell):**

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

*Примечание: Возможно, потребуется перезапустить терминал или добавить директорию Poetry в PATH. Следуйте
инструкциям [официальной документации Poetry](https://www.google.com/search?q=https://python-poetry.org/docs/%23installation).*

### 3\. Установка зависимостей

Перейдите в директорию проекта (если вы еще не там) и выполните:

```bash
poetry install
```

Эта команда создаст виртуальное окружение (если его нет) и установит все необходимые библиотеки, указанные
в `pyproject.toml`.

## Настройка

Перед запуском бота необходимо настроить переменные окружения.

1. Создайте файл `.env` в корневой директории проекта.

2. Добавьте в него токен вашего бота:

   ```dotenv
   BOT_TOKEN=ВАШ_ТЕЛЕГРАМ_БОТ_ТОКЕН
   ```

   Замените `ВАШ_ТЕЛЕГРАМ_БОТ_ТОКЕН` на реальный токен, полученный от [@BotFather](https://t.me/BotFather).

## Запуск приложения

Для запуска бота выполните команду:

```bash
poetry run python main.py
```

Бот начнет работу и будет обрабатывать входящие сообщения.

## Зависимости проекта

Полный список зависимостей и структура проекта описаны в файле `pyproject.toml`.

## Автор

* Vyacheslav1557 [@brawler2011](https://t.me/brawler2011)
