# -*- coding: utf-8 -*-
"""Backend проекта: генерация видео через Proxy API.

В уроке 10.4 эксперта используется OpenAI SDK с моделью sora-2.
Sora закрыта OpenAI (API отключён 24.09.2026), поэтому backend работает с
актуальным видео-API ProxyAPI (POST /v1/videos -> опрос статуса -> скачивание).
Пайплайн отлажен в задании 10.3, модель — x-ai/grok-imagine-video-1.5-lite.

Единая функция generate_video_with_progress() используется и ботом, и сайтом:
это наш backend, а bot.py и app.py — два frontend-канала к нему.
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.proxyapi.ru"
MODEL = os.getenv("VIDEO_MODEL", "x-ai/grok-imagine-video-1.5-lite")
DURATION = int(os.getenv("VIDEO_DURATION", "4"))   # секунды
RESOLUTION = os.getenv("VIDEO_RESOLUTION", "720p")
ASPECT = os.getenv("VIDEO_ASPECT", "1:1")
POLL_INTERVAL = 5          # как в уроке: опрос статуса каждые 5 секунд
TOTAL_TIMEOUT = 20 * 60    # максимум ожидания генерации, секунд
EST_TOTAL = 180            # оценка длительности генерации для прогресс-бара


def _headers():
    key = os.getenv("API_KEY")
    if not key:
        raise ValueError(
            "API_KEY не найден в переменных окружения. "
            "Добавьте его в файл .env (см. .env.example)"
        )
    return {"Authorization": f"Bearer {key}"}


def create_video_job(prompt):
    """Создаёт задачу генерации. Возвращает (job_id, статус)."""
    body = {
        "model": MODEL,
        "prompt": prompt,
        "resolution": RESOLUTION,
        "duration": DURATION,
        "aspect_ratio": ASPECT,
    }
    r = requests.post(f"{BASE}/v1/videos", headers=_headers(), json=body, timeout=60)
    r.raise_for_status()
    job = r.json()
    return job["id"], job.get("status", "pending")


def get_video_status(job_id):
    """Опрос статуса задачи (аналог client.videos.retrieve из урока)."""
    r = requests.get(f"{BASE}/v1/videos/{job_id}", headers=_headers(), timeout=60)
    r.raise_for_status()
    return r.json()


def _error_message(info):
    err = info.get("error")
    if isinstance(err, dict):
        return err.get("message") or "Генерация видео не удалась"
    if isinstance(err, str) and err:
        return err
    return "Генерация видео не удалась"


def download_video_file(info, video_path):
    """Скачивает готовый MP4 (аналог client.videos.download_content из урока)."""
    url = (info.get("unsigned_urls") or [None])[0]
    if not url:
        raise RuntimeError("Ссылка на готовое видео не найдена в ответе API")
    r = requests.get(url, headers=_headers(), timeout=300)
    r.raise_for_status()
    with open(video_path, "wb") as f:
        f.write(r.content)
    if not os.path.exists(video_path):
        raise RuntimeError("Файл не был создан после сохранения")
    return video_path


def generate_video_with_progress(prompt, on_update):
    """Генерация видео с прогрессом.

    on_update(status, progress, message) вызывается на каждом шаге;
    статусы — как в задании: queued / in_progress / downloading / completed / failed.
    ProxyAPI не отдаёт проценты выполнения, поэтому прогресс оценивается
    по времени (10% после создания задачи, +до 90% за EST_TOTAL секунд,
    95% на скачивании, 100% по готовности).
    Возвращает путь к сохранённому mp4 или бросает исключение.
    """
    on_update("queued", 5, "Задача создана, ставим в очередь")

    job_id, status = create_video_job(prompt)
    on_update("in_progress", 10, f"Модель {MODEL} приняла запрос, генерация началась")

    t0 = time.time()
    info = {}
    while time.time() - t0 < TOTAL_TIMEOUT:
        info = get_video_status(job_id)
        st = info.get("status", "pending")
        if st in ("completed", "succeeded"):
            break
        if st in ("failed", "error"):
            raise RuntimeError(_error_message(info))
        elapsed = int(time.time() - t0)
        progress = min(90, 10 + int(elapsed / EST_TOTAL * 80))
        on_update("in_progress", progress, f"Модель рисует кадры… прошло {elapsed} с")
        time.sleep(POLL_INTERVAL)
    else:
        raise RuntimeError("Превышено время ожидания генерации (20 минут)")

    on_update("downloading", 95, "Скачивание видео…")
    video_path = f"video_{job_id}.mp4"
    download_video_file(info, video_path)
    on_update("completed", 100, "Видео готово!")
    return video_path


if __name__ == "__main__":
    # Блок выполняется ТОЛЬКО при прямом запуске (python request.py).
    # При импорте из bot.py / app.py генерация не запускается — иначе каждый
    # импорт стоил бы денег и минут ожидания.
    demo_prompt = (
        "Крупный план чашки горячего кофе на деревянном столе, "
        "утренний свет сквозь жалюзи, мягкая глубина резкости."
    )
    path = generate_video_with_progress(
        demo_prompt,
        lambda status, progress, message: print(f"[{progress:3d}%] {status}: {message}"),
    )
    print("Готово:", path)
