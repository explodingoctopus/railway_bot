import asyncio
import http.server
import logging
import os
import sqlite3
import threading
import psycopg
from psycopg.rows import dict_row
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()  # Поддержка локального .env файла

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные из Railway или .env
def get_env(*names):
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None

BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN", "telegram_bot_token", "bot_token")
VIP_LINK = get_env("VIP_LINK", "vip_link")
CHANNEL_LINK = get_env("CHANNEL_LINK", "channel_link")
DATABASE_URL = get_env("DATABASE_URL", "database_url")
ADMIN_ID = get_env("ADMIN_ID", "admin_id")
DB_DRIVER = "postgres" if DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite"
SQLITE_PATH = "bot.db"


def connect_db():
    if DB_DRIVER == "postgres":
        return psycopg.connect(DATABASE_URL)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Инициализация БД
def init_db():
    try:
        with connect_db() as conn:
            if DB_DRIVER == "postgres":
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS subscribers (
                            user_id BIGINT PRIMARY KEY,
                            username VARCHAR(255),
                            first_name VARCHAR(255),
                            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
            else:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS subscribers (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        joined_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")

# Сохранение подписчика
def add_subscriber(user_id, username, first_name):
    try:
        with connect_db() as conn:
            if DB_DRIVER == "postgres":
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO subscribers (user_id, username, first_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id, username, first_name))
            else:
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR IGNORE INTO subscribers (user_id, username, first_name)
                    VALUES (?, ?, ?)
                """, (user_id, username, first_name))
            conn.commit()
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении: {e}")

# Получение всех подписчиков
def get_all_subscribers():
    try:
        with connect_db() as conn:
            if DB_DRIVER == "postgres":
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id FROM subscribers")
                    subscribers = cur.fetchall()
                return [sub['user_id'] for sub in subscribers]
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM subscribers")
            subscribers = cur.fetchall()
            return [sub['user_id'] for sub in subscribers]
    except Exception as e:
        logger.error(f"❌ Ошибка при получении подписчиков: {e}")
        return []

# Получение всех подписчиков в виде форматированной строки
def get_all_subscribers_list():
    try:
        with connect_db() as conn:
            if DB_DRIVER == "postgres":
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id, username, first_name, joined_at FROM subscribers ORDER BY joined_at ASC")
                    subscribers = cur.fetchall()
            else:
                cur = conn.cursor()
                cur.execute("SELECT user_id, username, first_name, joined_at FROM subscribers ORDER BY joined_at ASC")
                subscribers = cur.fetchall()
        if not subscribers:
            return "📋 Подписчиков пока нет."
        lines = ["📋 Все подписчики:"]
        for i, sub in enumerate(subscribers, start=1):
            username = f"@{sub['username']}" if sub['username'] else "—"
            name = sub['first_name'] or "—"
            joined_value = sub['joined_at']
            if hasattr(joined_value, "strftime"):
                joined = joined_value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                joined = joined_value or "—"
            lines.append(f"{i}. user_id: {sub['user_id']}, username: {username}, name: {name}, joined: {joined}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"❌ Ошибка при получении списка подписчиков: {e}")
        return "❌ Ошибка при получении списка подписчиков."


def get_db_status():
    try:
        with connect_db() as conn:
            if DB_DRIVER == "postgres":
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM subscribers")
                    count = cur.fetchone()[0]
            else:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM subscribers")
                count = cur.fetchone()[0]
        return {
            "ok": True,
            "driver": DB_DRIVER,
            "database_url": bool(DATABASE_URL),
            "subscriber_count": count,
        }
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке БД: {e}")
        return {"ok": False, "error": str(e)}


class StatusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/status"):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        status = get_db_status()
        if status["ok"]:
            body = (
                f"Bot status: running\n"
                f"DB driver: {status['driver']}\n"
                f"DATABASE_URL set: {status['database_url']}\n"
                f"Subscribers: {status['subscriber_count']}\n"
            )
            self.send_response(200)
        else:
            body = f"Bot status: error\nError: {status['error']}\n"
            self.send_response(500)

        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        return


def run_status_server(port: int):
    server_address = ("", port)
    httpd = http.server.ThreadingHTTPServer(server_address, StatusHandler)
    logger.info("🌐 Статус-сервер запущен на порту %s", port)
    httpd.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Трейдер"
    
    # Сохраняем подписчика
    add_subscriber(user.id, user.username, user.first_name)
    
    text = (
        f"👋 Привет, {name}!\n\n"
        f"Добро пожаловать в <b>Arlan Trading</b> 📈\n\n"
        f"Здесь я публикую:\n"
        f"• Торговые сигналы по Forex\n"
        f"• Анализ рынка и новости\n"
        f"• Обучающие материалы\n\n"
        f"🔥 Хочешь эксклюзивные сигналы с высокой точностью?\n"
        f"Вступай в <b>VIP группу</b> 👇"
    )
    
    buttons = []
    if VIP_LINK:
        buttons.append([InlineKeyboardButton("💎 Вступить в VIP группу", url=VIP_LINK)])
    if CHANNEL_LINK:
        buttons.append([InlineKeyboardButton("📢 Основной канал", url=CHANNEL_LINK)])

    keyboard = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Только для админа (твой ID)
    ADMIN_ID_VALUE = ADMIN_ID
    if ADMIN_ID_VALUE is not None:
        try:
            ADMIN_ID_VALUE = int(ADMIN_ID_VALUE)
        except ValueError:
            ADMIN_ID_VALUE = None

    if ADMIN_ID_VALUE is not None and update.effective_user.id != ADMIN_ID_VALUE:
        await update.message.reply_text("❌ У тебя нет прав на рассылку")
        return
    
    if not context.args:
        await update.message.reply_text("📝 Использование: /broadcast текст рассылки")
        return
    
    message_text = " ".join(context.args)
    subscribers = get_all_subscribers()
    
    if not subscribers:
        await update.message.reply_text("❌ Нет подписчиков")
        return
    
    sent = 0
    failed = 0
    
    for user_id in subscribers:
        try:
            await context.bot.send_message(chat_id=user_id, text=message_text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.error(f"Ошибка отправки {user_id}: {e}")
            failed += 1
    
    await update.message.reply_text(
        f"✅ Рассылка завершена\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ADMIN_ID_VALUE = ADMIN_ID
    if ADMIN_ID_VALUE is not None:
        try:
            ADMIN_ID_VALUE = int(ADMIN_ID_VALUE)
        except ValueError:
            ADMIN_ID_VALUE = None

    if ADMIN_ID_VALUE is not None and update.effective_user.id != ADMIN_ID_VALUE:
        await update.message.reply_text("❌ У тебя нет прав для просмотра подписчиков")
        return

    subscribers_list = get_all_subscribers_list()
    await update.message.reply_text(subscribers_list)

async def main():
    if not BOT_TOKEN:
        logger.error("❌ Не задано TELEGRAM_BOT_TOKEN")
        return

    if DB_DRIVER == "postgres" and not DATABASE_URL:
        logger.error("❌ Не задано DATABASE_URL для Postgres")
        return

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    port = int(os.environ.get("PORT", "8080"))
    logger.info("✅ Бот запущен и слушает Telegram polling")
    logger.info("🌐 Статус доступен на порту %s", port)

    status_thread = threading.Thread(target=run_status_server, args=(port,), daemon=True)
    status_thread.start()

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())