import asyncio
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = 31801207
API_HASH = "7aa0290e85951c6dd74ff1c45d722f43"

# Готовая строка сессии из твоих данных[cite: 2]
RAW_SESSION = (
    "1ApWw5bMBu7W1q3o4A2lZq...[данные сессии]"  # защищено от сбоев на Render
)

# Если токен сессии длинный, пропишем его прямо сюда:
SESSION_STRING = (
    "1BVtsO3IBu53V9...полная строка сессии из твоего файла...[cite: 2]"
)

os.makedirs("media_downloads/voices", exist_ok=True)
os.makedirs("media_downloads/video_notes", exist_ok=True)

app = Flask(__name__)


@app.route("/")
def home():
  return "System is active 24/7!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


ADMIN_CHAT_ID = None
client = None


async def main_telethon():
  global client

  # Используем StringSession, чтобы Render не искал физических файлов
  # Если строка пустая, пробуем пустую сессию, но с твоим дампом из базы:
  session_data = os.environ.get("SESSION_STRING", "")
  client = TelegramClient(StringSession(session_data), API_ID, API_HASH)

  @client.on(events.NewMessage(pattern="/start"))
  async def cmd_start(event):
    global ADMIN_CHAT_ID
    ADMIN_CHAT_ID = event.chat_id
    await event.respond(
        "🤖 Юзербот-радар запущен! Сюда летят логи.\nКоманды:\n/getlogs -"
        " скачать файл"
    )

  @client.on(events.NewMessage(pattern="/getlogs"))
  async def cmd_getlogs(event):
    if os.path.exists("messages.txt"):
      await event.respond(file="messages.txt", message="📂 Твои логи:")
    else:
      await event.respond("❌ Логи пока пусты.")

  @client.on(events.NewMessage(incoming=True))
  async def handle_incoming(event):
    if event.raw_text.startswith("/"):
      return

    sender = await event.get_sender()
    sender_name = ""
    sender_username = "нет"

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
          f"🎙 Голосовое от {sender_name} ({sender_username})\nФайл: {file_path}"
      )
      log_text = (
          f"[ГОЛОСОВОЕ] От: {sender_name} ({sender_username}) | {file_path}\n"
      )

    elif event.message.video_note:
      file_path = await event.message.download_media(
          file="media_downloads/video_notes/"
      )
      notification_text = (
          f"📹 Кружок от {sender_name} ({sender_username})\nФайл: {file_path}"
      )
      log_text = f"[КРУЖОК] От: {sender_name} ({sender_username}) | {file_path}\n"

    elif event.message.text:
      msg_content = event.raw_text
      notification_text = f"✉️ От: {sender_name} ({sender_username})\n💬 {msg_content}"
      log_text = (
          f"[ТЕКСТ] От: {sender_name} ({sender_username}) | {msg_content}\n"
      )

    if log_text:
      print(log_text, end="")
      with open("messages.txt", "a", encoding="utf-8") as f:
        f.write(log_text)

      if ADMIN_CHAT_ID:
        try:
          await client.send_message(ADMIN_CHAT_ID, notification_text)
        except Exception as e:
          print(f"Ошибка отправки: {e}")

  print("🚀 Запуск Telethon...")
  await client.start()
  await client.run_until_disconnected()


if __name__ == "__main__":
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  asyncio.run(main_telethon())
