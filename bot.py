# -*- coding: utf-8 -*-
"""Telegram-бот: frontend к backend-скрипту request.py.

Принимает любой текст как промпт, запускает генерацию в фоновом потоке и
обновляет ОДНО сообщение с прогресс-баром (edit_message_text), а не шлёт новые.
"""
import os
import threading

from dotenv import load_dotenv
import telebot

from request import generate_video_with_progress

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения. Добавьте его в .env файл")

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище задач: ключ — user_id (Telegram даёт его бесплатно, в отличие от сайта).
user_tasks = {}

STATUS_EMOJI = {
    "started": "🚀",
    "queued": "⏳",
    "in_progress": "⚙️",
    "downloading": "⬇️",
    "completed": "✅",
    "failed": "❌",
    "error": "❌",
}


def update_progress_message(user_id, message_id, status, progress, message_text):
    """Обновляет существующее сообщение: бар █░, эмодзи статуса, процент."""
    bar_length = 20
    filled_length = int((progress / 100) * bar_length)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    emoji = STATUS_EMOJI.get(status, "⏳")
    progress_text = f"{emoji} {message_text}\n\n[{bar}] {progress:.1f}%"
    try:
        bot.edit_message_text(progress_text, chat_id=user_id, message_id=message_id)
    except Exception:
        # «message not modified» и похожие мелочи не должны ронять генерацию
        pass


def _run_generation(prompt, user_id, message_id):
    def on_update(status, progress, message):
        user_tasks[user_id] = {
            "status": status,
            "progress": progress,
            "message": message,
            "video_id": user_tasks.get(user_id, {}).get("video_id"),
        }
        update_progress_message(user_id, message_id, status, progress, message)

    try:
        video_path = generate_video_with_progress(prompt, on_update)
        with open(video_path, "rb") as video_file:
            bot.send_video(user_id, video_file, caption="✅ Видео готово!")
        user_tasks[user_id]["video_id"] = video_path
    except Exception as e:
        user_tasks[user_id] = {
            "status": "failed",
            "progress": 100,
            "message": f"Ошибка: {e}",
            "video_id": None,
        }
        update_progress_message(user_id, message_id, "failed", 100, f"Ошибка: {e}")


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(
        message,
        "🎬 Привет! Я бот-генератор видео.\n"
        "Пришли мне описание сцены текстом — верну готовый ролик (4 сек, 720p).\n"
        "Пример: Кот в деловом костюме печатает на ноутбуке в офисе, вечерний город за окном.",
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Любое текстовое сообщение — это запрос на генерацию."""
    prompt = (message.text or "").strip()
    if not prompt:
        bot.reply_to(message, "Пришли описание сцены текстом 🙂")
        return

    user_tasks[message.from_user.id] = {
        "status": "started",
        "progress": 0,
        "message": "Генерация видео началась",
        "video_id": None,
    }
    msg = bot.send_message(message.chat.id, "🚀 Принял запрос, запускаю генерацию…")
    # Генерация в фоновом потоке: обработчик сразу освобождается для других сообщений
    threading.Thread(
        target=_run_generation, args=(prompt, message.chat.id, msg.message_id), daemon=True
    ).start()


if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
