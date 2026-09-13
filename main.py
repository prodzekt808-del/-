import os
import threading
import asyncio
from flask import Flask
from telethon import TelegramClient, events

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

# 2. Логика юзербота Telethon
ADMIN_CHAT_ID = None
client = None

async def main_telethon():
    global client
    # Создаем клиент внутри запущенного async-цикла, чтобы Python 3.14 не ругался
    client = TelegramClient("my_account", API_ID, API_HASH)

    @client.on(events.NewMessage(pattern='/start'))
    async def cmd_start(event):
        global ADMIN_CHAT_ID
        ADMIN_CHAT_ID = event.chat_id
        await event.respond("🤖 Бот-радар успешно подключен! Сюда будут падать все входящие сообщения.\nКоманды:\n/getlogs - скачать файл с логами")

    @client.on(events.NewMessage(pattern='/getlogs'))
    async def cmd_getlogs(event):
        if os.path.exists("messages.txt"):
            await event.respond(file='messages.txt', message="📂 Твой актуальный файл логов")
        else:
            await event.respond("❌ Файл логов пока пуст.")

    @client.on(events.NewMessage(incoming=True))
    async def handle_incoming(event):
        if event.raw_text.startswith('/'):
            return

        sender = await event.get_sender()
        sender_name = (getattr(sender, 'first_name', '') + ' ' + getattr(sender, 'last_name', '')).strip()
        sender_username = f"@{sender.username}" if getattr(sender, 'username', None) else "без юзернейма"

        log_text = ""
        notification_text = ""

        if event.message.voice:
            file_path = await event.message.download_media(file="media_downloads/voices/")
            notification_text = f"🎙 Новое голосовое!\n👤 От: {sender_name} ({sender_username})\n📁 Файл: {file_path}"
            log_text = f"[ГОЛОСОВОЕ] От: {sender_name} ({sender_username}) | Файл сохранен: {file_path}\n"

        elif event.message.video_note:
            file_path = await event.message.download_media(file="media_downloads/video_notes/")
            notification_text = f"📹 Новый кружок!\n👤 От: {sender_name} ({sender_username})\n📁 Файл: {file_path}"
            log_text = f"[КРУЖОК] От: {sender_name} ({sender_username}) | Файл сохранен: {file_path}\n"

        elif event.message.text:
            msg_content = event.raw_text
            notification_text = f"✉️ Новое сообщение!\n👤 От: {sender_name} ({sender_username})\n💬 Текст: {msg_content}"
            log_text = f"[ТЕКСТ] От: {sender_name} ({sender_username}) | Текст: {msg_content}\n"

        if log_text:
            print(log_text, end="")
            with open("messages.txt", "a", encoding="utf-8") as f:
                f.write(log_text)

            if ADMIN_CHAT_ID:
                try:
                    await client.send_message(ADMIN_CHAT_ID, notification_text)
                except Exception as e:
                    print(f"Ошибка отправки уведомления: {e}")

    print("🚀 Запуск Telethon...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    # Запускаем Flask в фоне
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем Asyncio-цикл для Telethon в главном потоке
    asyncio.run(main_telethon())
