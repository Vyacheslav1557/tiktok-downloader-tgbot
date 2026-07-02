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

## Деплой (CI/CD)

В проекте настроен автоматический деплой на сервер с помощью GitHub Actions при создании релизного тега (шаблон `v*`, например `v1.0.0`).

Для корректной работы деплоя перейдите в настройки вашего репозитория на GitHub (**Settings -> Secrets and variables -> Actions**) и добавьте следующие секреты в **Repository secrets**:

* `SSH_HOST` — IP-адрес или хост вашего сервера.
* `SSH_USER` — имя пользователя для подключения по SSH (например, `root` или `ubuntu`).
* `SSH_KEY` — приватный SSH-ключ для подключения к серверу.
* `BOT_TOKEN` — API-токен вашего Telegram-бота.
* `SSH_PORT` — *(опционально)* порт для SSH-подключения, если он отличается от стандартного `22`.

### Процесс деплоя:
1. Запуште все изменения в ветку `main`.
2. Создайте и отправьте релизный тег в репозиторий:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. GitHub Actions автоматически соберет Docker-образ, опубликует его в GitHub Container Registry (GHCR) и обновит запущенный контейнер на вашем сервере через Docker Compose.

## Автор

* Brawler2011 [@brawler2011](https://t.me/brawler2011)
