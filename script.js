// Логика страницы: POST /generate -> task_id, дальше опрос /status/<task_id>
// каждые 3 секунды. Готовое видео показываем плеером и кнопкой скачивания.
// Последний task_id сохраняется в localStorage: после обновления страницы
// статус и скачивание восстанавливаются.

const form = document.getElementById("video-form");
const promptInput = document.getElementById("prompt");
const generateBtn = document.getElementById("generate-btn");
const statusBlock = document.getElementById("status");
const barWrap = document.getElementById("bar-wrap");
const bar = document.getElementById("bar");
const resultBlock = document.getElementById("result-block");
const videoEl = document.getElementById("video");
const downloadLink = document.getElementById("download-link");
const taskInfo = document.getElementById("task-info");

const STATUS_EMOJI = {
  queued: "⏳",
  in_progress: "⚙️",
  downloading: "⬇️",
  completed: "✅",
  failed: "❌",
};

function showStatus(text, isError) {
  statusBlock.textContent = text;
  statusBlock.classList.remove("hidden");
  statusBlock.classList.toggle("error", Boolean(isError));
}

function setProgress(status, progress, message) {
  const emoji = STATUS_EMOJI[status] || "⏳";
  showStatus(`${emoji} ${message || status} — ${progress}%`, status === "failed");
  barWrap.classList.remove("hidden");
  bar.style.width = progress + "%";
}

function showResult(taskId) {
  bar.style.width = "100%";
  const url = `/download/${taskId}`;
  videoEl.src = url;
  downloadLink.href = url;
  resultBlock.classList.remove("hidden");
  showStatus("✅ Видео готово! Можно посмотреть, скачать или перезайти по ссылке позже.");
  generateBtn.disabled = false;
  generateBtn.textContent = "Начать генерацию";
}

function showError(message) {
  showStatus("❌ " + message, true);
  generateBtn.disabled = false;
  generateBtn.textContent = "Начать генерацию";
}

async function pollStatus(taskId) {
  const response = await fetch(`/status/${taskId}`);
  if (!response.ok) {
    localStorage.removeItem("last_task_id");
    showError("Задача не найдена — возможно, сайт перезапускался. Запустите генерацию заново.");
    return;
  }
  const task = await response.json();
  setProgress(task.status, task.progress, task.message);
  if (task.status === "completed") {
    showResult(taskId);
  } else if (task.status === "failed") {
    showError(task.message || "Генерация не удалась");
  } else {
    setTimeout(() => pollStatus(taskId), 3000);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) {
    showStatus("Введите промпт — без него модель не знает, что рисовать.", true);
    return;
  }
  generateBtn.disabled = true;
  generateBtn.textContent = "Запускаем…";
  showStatus("Отправляем запрос на сервер…");
  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      showError(data.error || "Не удалось запустить генерацию");
      return;
    }
    localStorage.setItem("last_task_id", data.task_id);
    showStatus(`Задача ${data.task_id.slice(0, 8)}… запущена, ждём модель.`);
    pollStatus(data.task_id);
  } catch (err) {
    showError("Ошибка сети: " + err.message);
  }
});

// Восстановление после обновления страницы: если задача ещё жива — досматриваем
window.addEventListener("load", () => {
  const last = localStorage.getItem("last_task_id");
  if (last) {
    taskInfo.textContent = `Продолжаем задачу ${last.slice(0, 8)}…`;
    pollStatus(last);
  }
});
