# railway_bot

Простой Telegram-бот для рассылки и сохранения подписчиков.

## Как использовать

1. Задай токен нового бота от BotFather в переменную окружения `TELEGRAM_BOT_TOKEN` или `telegram_bot_token`.
2. Установи ссылки в `VIP_LINK` / `vip_link` и `CHANNEL_LINK` / `channel_link` через переменные окружения.
3. Если ты не хочешь подключать PostgreSQL, оставь `DATABASE_URL` пустым — бот будет автоматически использовать локальную SQLite-базу `bot.db`.
4. Установи `ADMIN_ID` или `admin_id` для команды `/broadcast` и `/users`.

### Локальная настройка через `.env`

Создай файл `.env` в корне проекта с такими значениями:

```ini
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
VIP_LINK=https://t.me/arlan_trade?text=СИГНАЛЫ
CHANNEL_LINK=https://t.me/+Q0_mA5CQbhE4M2Yy
DATABASE_URL=postgresql://user:password@host:port/dbname
ADMIN_ID=123456789
```

### Пример для локального запуска

```bash
bash start_bot.sh
```

Если бот уже запущен и нужно его перезапустить, нажми `Ctrl+C` в терминале, а затем снова `bash start_bot.sh`.

> ⚠️ Токен бота нельзя выкладывать публично. Если токен уже был скомпрометирован, лучше сгенерировать новый.

## Railway

1. Подключи репозиторий к Railway.
2. Создай проект, выбери `Deploy from GitHub` или `Deploy from repo`.
3. В настройках проекта добавь переменные окружения:
   - `TELEGRAM_BOT_TOKEN`
   - `VIP_LINK`
   - `CHANNEL_LINK`
   - `DATABASE_URL` (если хочешь использовать Railway PostgreSQL и сохранить базу между перезапусками)
   - `ADMIN_ID`
4. Railway автоматически установит зависимости из `requirements.txt`.
5. Бот запускается командой из `Procfile`:

```text
web: python bot.py
```
## Автоматический деплой

Добавлен GitHub Actions workflow `.github/workflows/deploy.yml`, который может деплоить проект в Railway при пуше в `main`.

Для работы workflow нужно создать секрет GitHub `RAILWAY_API_KEY` и установить туда ключ Railway API.

После этого каждое обновление в ветке `main` будет автоматически пытаться задеплоить проект.
> Этот проект теперь запускает HTTP-статус на корневом пути `/`, чтобы Railway видел живой веб-процесс. Если ты добавишь Railway PostgreSQL, сервис будет подключаться к ней через `DATABASE_URL`.

## Команды бота

- `/start` — сохранить пользователя в базу и показать ссылки на VIP и канал.
- `/broadcast текст` — отправить сообщение всем подписчикам (доступно только администратору).
- `/users` — получить список всех подписчиков (только администратор).

## База данных подписчиков

Когда пользователь нажимает `/start`, его `user_id`, `username` и `first_name` сохраняются в таблицу `subscribers`.
Если `DATABASE_URL` не задан, бот использует локальную SQLite-базу `bot.db`.

## Зависимости

```bash
pip install -r requirements.txt
```
