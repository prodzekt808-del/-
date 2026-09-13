import asyncio
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = 31801207
API_HASH = "7aa0290e85951c6dd74ff1c45d722f43"
# Вставь сюда длинную строку сессии, которую тебе выдал Colab:
SESSION_STRING = "ВСЮ_ЭТУ_ДЛИННУЮ_СТРОКУ_СЮДА"

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


# 2. Логика юзербота Telethon через StringSession
ADMIN_CHAT_ID = None
client = None


async def main_telethon():
  global client

  # Запуск через строковую сессию — никаких файлов не нужно!
  client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

  @client.on(events.NewMessage(pattern="/start"))
  async def cmd_start(event):
    global ADMIN_CHAT_ID
    ADMIN_CHAT_ID = event.chat_id
    await event.respond(
        "🤖 Юзербот-радар успешно подключен! Сюда будут падать все входящие"
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
    if event.raw_text.startswith("/"):
      return

    sender = await event.get_sender()
    sender_name = ""
    sender_username = "без юзернейма"

    if sender:
      sender_name = (getattr(sender, "first_name", "") or "") + " " + (
          getattr(sender, "last_name", "") or ""
      )
      sender_name = sender_name.strip()
      if getattr(sender, "username", None):
        sender_username = f"@{sender.username}"

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

      if ADMIN_CHAT_ID:
        try:
          await client.send_message(ADMIN_CHAT_ID, notification_text)
        except Exception as e:
          print(f"Ошибка отправки уведомления: {e}")

  print("🚀 Запуск Telethon по строковой сессии...")
  await client.start()
  await client.run_until_disconnected()


if __name__ == "__main__":
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  asyncio.run(main_telethon())
