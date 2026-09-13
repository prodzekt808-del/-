import os
import threading
from flask import Flask
from telethon import TelegramClient, events

# Твои данные api_id и api_hash (с my.telegram.org)
API_ID = int(os.environ.get("API_ID", 1234567))
API_HASH = os.environ.get("API_HASH", "твой_api_hash")

os.makedirs("media_downloads/voices", exist_ok=True)
os.makedirs("media_downloads/video_notes", exist_ok=True)

# 1. Веб-сервер Flask для удержания Render 24/7
app = Flask(__name__)


@app.route("/")
def home():
  return "System is active 24/7!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# 2. Клиент Telethon (работает и как аккаунт, и может отвечать на команды)
# Файл сессии 'my_account.session' создастся автоматически
client = TelegramClient("my_account", API_ID, API_HASH)

ADMIN_CHAT_ID = None


@client.on(events.NewMessage(pattern="/start"))
async def cmd_start(event):
  global ADMIN_CHAT_ID
  ADMIN_CHAT_ID = event.chat_id
  await event.respond(
      "🤖 Бот-радар успешно подключен! Сюда будут падать все входящие"
      " сообщения.\nКоманды:\n/getlogs - скачать файл с логами"
  )


@client.on(events.NewMessage(pattern="/getlogs"))
async def cmd_getlogs(event):
  if os.path.exists("messages.txt"):
    await event.respond(
        file="messages.txt", message="📂 Твой актуальный файл логов"
    )
  else:
    await event.respond("❌ Файл логов пока пуст.")


@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event):
  # Игнорируем команды
  if event.raw_text.startswith("/"):
    return

  sender = await event.get_sender()
  sender_name = (
      getattr(sender, "first_name", "") + " " + getattr(sender, "last_name", "")
  ).strip()
  sender_username = (
      f"@{sender.username}" if getattr(sender, "username", None) else "без юзернейма"
  )

  log_text = ""
  notification_text = ""

  if event.message.voice:
    file_path = await event.message.download_media(file="media_downloads/voices/")
    notification_text = (
        f"🎙 Новое голосовое!\n👤 От: {sender_name} ({sender_username})\n📁 Файл:"
        f" {file_path}"
    )
    log_text = (
        f"[ГОЛОСОВОЕ] От: {sender_name} ({sender_username}) | Файл сохранен:"
        f" {file_path}\n"
    )

  elif event.message.video_note:
    file_path = await event.message.download_media(
        file="media_downloads/video_notes/"
    )
    notification_text = (
        f"📹 Новый кружок!\n👤 От: {sender_name} ({sender_username})\n📁 Файл:"
        f" {file_path}"
    )
    log_text = (
        f"[КРУЖОК] От: {sender_name} ({sender_username}) | Файл сохранен:"
        f" {file_path}\n"
    )

  elif event.message.text:
    msg_content = event.raw_text
    notification_text = (
        f"✉️ Новое сообщение!\n👤 От: {sender_name}"
        f" ({sender_username})\n💬 Текст: {msg_content}"
    )
    log_text = (
        f"[ТЕКСТ] От: {sender_name} ({sender_username}) | Текст:"
        f" {msg_content}\n"
    )

  if log_text:
    print(log_text, end="")
    with open("messages.txt", "a", encoding="utf-8") as f:
      f.write(log_text)

    # Отправляем уведомление в чат, если админ нажал /start
    if ADMIN_CHAT_ID:
      try:
        await client.send_message(ADMIN_CHAT_ID, notification_text)
      except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")


if __name__ == "__main__":
  # Запускаем Flask в фоне
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  print("🚀 Запуск Telethon...")
  client.start()
  client.run_until_disconnected()
