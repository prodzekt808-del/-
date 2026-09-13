import asyncio
import os
import threading
from aiogram import Bot, Dispatcher, executor, types
from flask import Flask
from telethon import TelegramClient, events

# Твои данные api_id и api_hash (с my.telegram.org)
API_ID = int(os.environ.get("API_ID", 1234567))  # Замени на свой api_id
API_HASH = os.environ.get("API_HASH", "твой_api_hash")  # Замени на свой api_hash
STRING_SESSION = os.environ.get("STRING_SESSION", "")

# Токен твоего Telegram-бота для управления и уведомлений
TELEGRAM_BOT_TOKEN = "8832101383:AAE7F7Bu8UXojz420PnW0rXJeDGCZkpq4o0"
# Твой Telegram ID (или чат, куда бот будет присылать уведомления).
# Если оставить пустым, бот пришлет уведомление первому, кто ему напишет.
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

os.makedirs("media_downloads/voices", exist_ok=True)
os.makedirs("media_downloads/video_notes", exist_ok=True)

# 1. Запуск мини-сервера Flask (чтобы Render не усыплял приложение)
app = Flask(__name__)


@app.route("/")
def home():
  return "System is active 24/7!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# 2. Настройка Aiogram-бота (для отправки уведомлений и команд)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)


async def send_notification(text):
  """Функция отправки уведомления в твой чат с ботом"""
  if ADMIN_CHAT_ID:
    try:
      await bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=text)
    except Exception as e:
      print(f"Ошибка отправки уведомления ботом: {e}")


@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
  global ADMIN_CHAT_ID
  ADMIN_CHAT_ID = str(message.chat.id)
  await message.answer(
      "🤖 Бот-радар подключен! Сюда будут падать все входящие сообщения."
      " Команды:\n/getlogs - скачать файл с логами"
  )


@dp.message_handler(commands=["getlogs"])
async def cmd_getlogs(message: types.Message):
  if os.path.exists("messages.txt"):
    with open("messages.txt", "rb") as f:
      await message.answer_document(f, caption="📂 Твой актуальный файл логов")
  else:
    await message.answer("❌ Файл логов пока пуст.")


def run_aiogram_bot():
  # Запускаем поллинг официального бота в отдельном цикле событий
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  executor.start_polling(dp, skip_updates=True)


# 3. Настройка юзербота Telethon (следит за сообщениями)
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)


@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event):
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
        f"🎙 <b>Новое голосовое!</b>\n👤 От: {sender_name} ({sender_username})\n📁"
        f" Файл: {file_path}"
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
        f"📹 <b>Новый кружок!</b>\n👤 От: {sender_name} ({sender_username})\n📁"
        f" Файл: {file_path}"
    )
    log_text = (
        f"[КРУЖОК] От: {sender_name} ({sender_username}) | Файл сохранен:"
        f" {file_path}\n"
    )

  elif event.message.text:
    msg_content = event.raw_text
    notification_text = (
        f"✉️ <b>Новое сообщение!</b>\n👤 От: {sender_name}"
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

    # Отправляем мгновенное уведомление в твой Telegram-бот
    if ADMIN_CHAT_ID:
      loop = asyncio.get_event_loop()
      asyncio.run_coroutine_threadsafe(
          send_notification(notification_text), loop
      )


def run_telegram_userbot():
  print("🚀 Юзербот запущен...")
  client.start()
  client.run_until_disconnected()


if __name__ == "__main__":
  # Запускаем Flask-сервер в фоне
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  # Запускаем официального бота в фоне
  bot_thread = threading.Thread(target=run_aiogram_bot)
  bot_thread.daemon = True
  bot_thread.start()

  # Запускаем юзербота (основной поток)
  run_telegram_userbot()
