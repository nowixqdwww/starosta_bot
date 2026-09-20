# Староста: Telegram Mini App

Регистрация старосты и студентов, приглашения по коду. Расписание и посещаемость идут следующими шагами.

## Запуск

    pip install -r requirements.txt
    cp .env.example .env        # впиши BOT_TOKEN, BOT_USERNAME, APP_SHORTNAME
    uvicorn app.main:app --env-file .env --reload

Mini App работает только по HTTPS. Локально удобно пробросить порт через ngrok или cloudflared,
а затем в BotFather:

1. `/newapp` (или Bot Settings, Menu Button), указать HTTPS-адрес сервиса.
2. Короткое имя приложения записать в `APP_SHORTNAME`: по нему собирается ссылка-приглашение
   `https://t.me/<бот>/<приложение>?startapp=КОД`.

## Структура

    app/main.py      API: /api/me, /api/invite/{code}, /api/register/leader, /api/register/student
    app/auth.py      проверка подписи initData от Telegram
    app/models.py    таблицы groups и users
    static/          сам Mini App (index.html, style.css, app.js)
    test_step1.py    тест API с самоподписанной initData
