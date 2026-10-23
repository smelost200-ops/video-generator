# Генератор видео — Telegram-бот + Flask-сайт (PE10.4)

Учебный проект: обёртка AI-скрипта генерации видео (урок 10.3) в пользовательский
интерфейс: Telegram-бот и Flask-сайт, развёртывание на сервере 24/7.

## Архитектура

```
┌────────────┐      ┌──────────────┐      ┌──────────────────────┐
│  Telegram  │      │ Flask-сайт   │      │  Proxy API (/v1/videos)│
│  bot.py    │─────▶│ app.py       │─────▶│  grok-imagine-video    │
└────────────┘      └──────────────┘      └──────────────────────┘
        └────────────┴──── request.py — общий backend ─────┘
```

- **request.py** — backend: создание задачи, опрос статуса, скачивание MP4,
  общая функция `generate_video_with_progress(prompt, on_update)` со статусами
  queued / in_progress / downloading / completed / failed.
- **bot.py** — frontend №1: прогресс-бар через `edit_message_text` (одно
  сообщение), готовое видео отправляется в чат (`send_video`).
- **app.py** — frontend №2: task_id через `uuid.uuid4()`, потоки `threading`,
  роуты `/`, `/generate`, `/status/<task_id>`, `/download/<task_id>`.
  Видео хранится на сервере — скачивание работает и после обновления страницы.

> Почему не `client.videos.create(model="sora-2")`, как в уроке: OpenAI закрыла
> Sora (API отключён 24.09.2026). Backend работает с актуальным видео-API
> ProxyAPI через REST — тот же пайплайн, что отлажен в задании 10.3
> (модель `x-ai/grok-imagine-video-1.5-lite`). ProxyAPI не отдаёт проценты
> генерации, поэтому прогресс-бар оценивает ход по времени.

## Локальный запуск

```bash
python -m venv venv
# Windows: venv\Scripts\activate   |   Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # и заполнить API_KEY и BOT_TOKEN
```

- Бот: `python bot.py`
- Сайт: `python app.py` → http://localhost:5000
- Проверка backend отдельно: `python request.py` (запустит демо-генерацию
  «чашка кофе» — по конструкции `if __name__ == "__main__"` при импорте
  ничего не генерирует).

## Развёртывание на сервере (24/7)

```bash
ssh root@<IP_сервера>
git clone <ссылка_на_репозиторий> && cd <папка_проекта>
apt install python3.12-venv -y
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
nano .env                    # заполнить API_KEY и BOT_TOKEN; Ctrl+X, Y, Enter

screen -S bot                # терминал 1: бот
python bot.py                # затем Ctrl+A, D — свернуть в фон

screen -S site               # терминал 2: сайт
python app.py                # уже с host='0.0.0.0', debug=False
                             # Ctrl+A, D — свернуть

screen -ls                   # оба процесса должны висеть в списке
```

Сайт открывается по `http://<IP_сервера>:5000`. После закрытия SSH-сессии
процессы в screen продолжают работать. Вернуться: `screen -r bot` /
`screen -r site`; остановить: Ctrl+C, затем `exit`.

## Ключи и безопасность

- `.env` в `.gitignore` — реальные ключи не попадают на GitHub.
- В репозитории лежит `.env.example` с названиями переменных.

## Чек-лист отчёта (ДЗ)

1. Скриншот бота в Telegram (имя + юзернейм от BotFather).
2. Переписка с ботом: промпт → прогресс-бар (одно обновляемое сообщение) → видео в чате.
3. Сайт: введённый промпт + идущий прогресс-бар.
4. Страница/кнопка скачивания видео.
5. `screen -ls` на сервере (два screen: bot, site).
6. Репозиторий на GitHub.
7. Ссылка на репозиторий + текстовое описание (5–10 предложений).
