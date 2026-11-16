# tg-booking-bot

[![CI](https://github.com/lir147/tg-booking-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/lir147/tg-booking-bot/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0)
![License](https://img.shields.io/badge/license-MIT-green)

Telegram-бот «визитка с записью» для малого бизнеса: барбершопов, автосервисов,
кофеен, салонов. Клиент выбирает услугу, видит цену и свободное время,
записывается в два нажатия. Администратор получает заявку в Telegram.

## Возможности

- **Запись в два клика.** Услуга → цена и свободные окна → подтверждение с адресом.
- **Без двойных записей.** Занятое время пропадает из списка. Одновременные
  нажатия разрешает ограничение `UNIQUE` в БД, а не проверка в коде.
- **Вопросы администратору.** Клиент пишет вопрос, бот пересылает его админу.
  Админ отвечает реплаем, и ответ уходит клиенту.
- **Уведомления о записях** и команда `/bookings` со списком предстоящих визитов.
- **Настройка без программиста.** Услуги, цены, расписание и все тексты лежат в одном JSON.
  Правки подхватываются на лету, без перезапуска. Если в файле ошибка, бот
  продолжит работать на последней корректной версии.
- **Готовые профили:** `barbershop`, `autoservice`, `cafe`. Переключаются одной переменной.
- **Расписание:** окна по времени, горизонт в днях, выходные, минимальный запас до визита.

## Стек

Python 3.11+, aiogram 3, SQLite, pytest, ruff, Docker, GitHub Actions.

## Быстрый старт

```bash
git clone https://github.com/lir147/tg-booking-bot.git
cd tg-booking-bot
cp .env.example .env          # впишите BOT_TOKEN и ADMIN_ID
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m bot
```

> Администратор должен один раз написать боту `/start`, иначе Telegram не даст
> боту отправить ему уведомление.

### Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Папка `configs/` смонтирована в контейнер, так что тексты и цены можно править
без пересборки образа.

### systemd

Пример юнита лежит в [`deploy/booking-bot.service`](deploy/booking-bot.service).

## Настройка

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | токен от [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Telegram ID администратора ([@userinfobot](https://t.me/userinfobot)) |
| `BUSINESS_CONFIG` | профиль бизнеса, по умолчанию `configs/barbershop.json` |
| `DB_PATH` | путь к SQLite, по умолчанию `data/bookings.db` |

Профиль бизнеса (`configs/*.json`):

```jsonc
{
  "business_name": "Барбершоп «Бритва»",
  "address": "ул. Ленина, 1",
  "phone": "+7 900 000-00-00",
  "work_hours_text": "ежедневно 10:00–21:00",
  "timezone": "Europe/Moscow",
  "services": [
    { "name": "✂️ Мужская стрижка", "price": "1 200 ₽", "description": "~45 минут" }
  ],
  "slots": {
    "times": ["10:00", "12:00", "15:00", "18:00"],
    "days_ahead": 3,          // сколько дней показывать
    "days_off": [6],          // 0 = пн … 6 = вс
    "min_lead_minutes": 60,   // не раньше чем через час
    "max_buttons": 8
  },
  "texts": { "greeting": "Здравствуйте, {name}! …" }
}
```

В текстах доступны подстановки `{name}`, `{business}`, `{service}`, `{price}`,
`{slot}`, `{address}`, `{phone}`. Разметка: HTML (`<b>`, `<i>`).

## Структура

```
bot/
├── __main__.py        # точка входа, сборка Dispatcher и DI
├── config.py          # Settings из env, профиль бизнеса с hot-reload
├── slots.py           # расчёт свободных окон (чистая логика, без Telegram)
├── storage.py         # репозиторий записей на SQLite
├── keyboards.py       # клавиатуры и типизированные CallbackData
└── handlers/
    ├── client.py      # сценарий клиента и FSM вопроса
    └── admin.py       # ответы клиентам, /bookings
configs/               # профили бизнеса
tests/                 # pytest
```

Бизнес-логика (`slots`, `storage`, `config`) не зависит от aiogram и тестируется
изолированно. Хендлеры получают зависимости через DI диспетчера.

## Разработка

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

## Лицензия

MIT
