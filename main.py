import asyncio
import os
import threading
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from flask import Flask
from telethon import TelegramClient, events

# Твои данные api_id и api_hash (с my.telegram.org)
API_ID = int(os.environ.get("API_ID", 1234567))
API_HASH = os.environ.get("API_HASH", "твой_api_hash")

# Токен твоего официального Telegram-бота для уведомлений
TELEGRAM_BOT_TOKEN = "8832101383:AAE7F7Bu8UXojz420PnW0rXJeDGCZkpq4o0"
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

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


# 2. Настройка Bot (aiogram 3.x)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


async def send_notification(text):
  global ADMIN_CHAT_ID
  if ADMIN_CHAT_ID:
    try:
      await bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=text)
    except Exception as e:
      print(f"Ошибка отправки уведомления: {e}")


@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message):
  global ADMIN_CHAT_ID
  ADMIN_CHAT_ID = str(message.chat.id)
  await message.answer(
      "🤖 Бот-радар подключен! Сюда будут падать все входящие сообщения."
      " Команды:\n/getlogs - скачать файл с логами"
  )


@dp.message(Command("getlogs"))
async def cmd_getlogs(message: types.Message):
  if os.path.exists("messages.txt"):
    document = types.FSInputFile("messages.txt")
    await message.answer_document(
        document, caption="📂 Твой актуальный файл логов"
    )
  else:
    await message.answer("❌ Файл логов пока пуст.")


def run_aiogram_bot():
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  loop.run_until_complete(dp.start_polling(bot))


# 3. Юзербот Telethon с файловой сессией (спросит один раз и запомнит)
# Имя файла сессии 'my_account.session' сохранится на сервере, больше код просить не будет
client = TelegramClient("my_account", API_ID, API_HASH)


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
      loop = asyncio.get_event_loop()
      asyncio.run_coroutine_threadsafe(
          send_notification(notification_text), loop
      )


def run_telegram_userbot():
  print("🚀 Юзербот запущен...")
  # При первом запуске попросит ввести номер и код в консоли Render (в логах деплоя),
  # после чего создаст файл сессии и больше никогда не будет переспрашивать.
  client.start()
  client.run_until_disconnected()


if __name__ == "__main__":
  # Запускаем Flask в фоне
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  # Запускаем бота в фоне
  bot_thread = threading.Thread(target=run_aiogram_bot)
  bot_thread.daemon = True
  bot_thread.start()

  # Запускаем юзербота
  run_telegram_userbot()
