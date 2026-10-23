# -*- coding: utf-8 -*-
"""Flask-сайт: второй frontend к backend-скрипту request.py.

Отличия от Telegram-бота (это спрашивают в отчёте):
1. Нет готового user_id от Telegram — идентификатор задачи генерируем сами
   через uuid.uuid4() и отдаём пользователю.
2. Видео НЕ удаляется после отправки: файл лежит на сервере, чтобы скачивание
   работало даже после обновления страницы или повторного захода по task_id.
"""
import os
import uuid
import threading

from flask import Flask, request, jsonify, render_template, send_file
from dotenv import load_dotenv

from request import generate_video_with_progress

load_dotenv()

app = Flask(__name__)

# Хранилище состояния задач: task_id -> {status, progress, message, video_path}
tasks = {}


def _run_task(prompt, task_id):
    def on_update(status, progress, message):
        tasks[task_id] = {
            "status": status,
            "progress": progress,
            "message": message,
            "video_path": tasks.get(task_id, {}).get("video_path"),
        }

    try:
        video_path = generate_video_with_progress(prompt, on_update)
        tasks[task_id]["video_path"] = video_path
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "progress": 100,
            "message": f"Ошибка: {e}",
            "video_path": None,
        }


@app.route("/")
def index():
    """Главная страница: форма ввода промпта."""
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Запуск генерации: создаём task_id и задачу в отдельном потоке."""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Пустой промпт: опишите сцену текстом"}), 400
    if not os.getenv("API_KEY"):
        return jsonify({"error": "API_KEY не настроен — заполните файл .env"}), 500

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Задача поставлена в очередь",
        "video_path": None,
    }
    thread = threading.Thread(target=_run_task, args=(prompt, task_id))
    thread.daemon = True
    thread.start()
    return jsonify({"task_id": task_id})


@app.route("/status/<task_id>")
def status(task_id):
    """Проверка статуса задачи (страница опрашивает её каждые 3 секунды)."""
    if task_id not in tasks:
        return jsonify({"error": "Задача не найдена"}), 404
    task = dict(tasks[task_id])
    task.pop("video_path", None)  # путь — внутренняя деталь, наружу не отдаём
    return jsonify(task)


@app.route("/download/<task_id>")
def download(task_id):
    """Скачивание готового видео. Работает и после обновления страницы."""
    if task_id not in tasks:
        return jsonify({"error": "Задача не найдена"}), 404
    task = tasks[task_id]
    video_path = task.get("video_path")
    if not video_path or not os.path.exists(video_path):
        return jsonify({
            "error": "Видео ещё не готово",
            "status": task["status"],
            "message": task.get("message", "Ожидание..."),
        }), 400
    try:
        return send_file(video_path, as_attachment=True, download_name="video.mp4")
    except Exception as e:
        return jsonify({"error": f"Ошибка при отправке файла: {e}"}), 500


if __name__ == "__main__":
    # На сервере: host='0.0.0.0' (принимать запросы со всех IP) и debug=False
    # (не показывать ошибки пользователю). В Colab это тоже корректно работает.
    app.run(host="0.0.0.0", port=5000, debug=False)
