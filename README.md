<div align="center">

# ⚔️ DnD Solo

**Соло-RPG в D&D 5e, где роль Мастера (DM) исполняет локальная LLM**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-MVP-orange)](#-текущий-статус)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Caracoto4/DnD-Solo)

Всё работает **оффлайн**. LLM отвечает только за нарратив — вся механика
считается движком.

[Возможности](#-возможности) •
[Быстрый старт](#-быстрый-старт) •
[Архитектура](#-архитектура) •
[API](#-api) •
[Дорожная карта](#-дорожная-карта)

</div>

---

## 📖 О проекте

**DnD Solo** — платформа для одиночной игры в D&D 5e. Роль Мастера подменивает
локальная LLM, запущенная через **[koboldcpp](https://github.com/LostRuins/koboldcpp)**
(OpenAI-совместимый эндпоинт). Ключевой принцип — **LLM не может менять числа
напрямую**:

- LLM отвечает **только за нарратив**, диалоги NPC и описание мира.
- Вся механика (HP, статы, инвентарь, слоты, броски, квесты, состояния)
  считается программно **движком**.
- LLM запрашивает изменения через строгий **JSON-протокол**, который
  валидируется движком (`state_changes`). Броски урона по формуле (`"2d6"`)
  выполняются движком, а не LLM.

> 📄 Оригинальное техническое задание — в [`dnd-solo/docs/ТЗ.md`](dnd-solo/docs/ТЗ.md).

<div align="center">

![Интерфейс игры](https://placehold.co/900x520/241c15/e8dcc8?text=DnD+Solo+%E2%80%94+chat+%2B+character+panel+%2B+dice&font=serif)
<sub><i>Скриншот временного веб-интерфейса (появится после итерации 2)</i></sub>

</div>

## ✨ Возможности

- 🎭 **LLM-мастер** — нарратив, NPC и мир генерируются локальной моделью через koboldcpp
- 🧮 **Строгий JSON-протокол** — LLM может только *запросить* изменение, движок валидирует и применяет
- 🎲 **Dice Roller** — формулы `2d6+3`, `1d20+5 adv/dis`, `4d6dl1`; кубы крутит движок
- 🌐 **RU↔EN перевод** — пишете по-русски, LLM отвечает на английском, всё переводится обратно; кэш переводов в SQLite защитит от лимитов Google
- 💾 **Save / Load / Undo** — снапшоты состояния и откат последнего хода
- 📊 **Панель персонажа** — HP-бар, КД, характеристики, состояния, инвентарь, квесты, мир
- 🪶 **Theater of the Mind** — бой без сетки, абстрактные позиции
- 📝 **Логирование** — все LLM-запросы и ответы пишутся в SQLite для отладки

## 🧰 Технологии

| Слой | Технология |
|---|---|
| Backend | Python 3.12, FastAPI, uvicorn |
| LLM-сервер | koboldcpp (OpenAI-совместимый `/v1/chat/completions`) |
| База данных | SQLite — переводы, сейвы, undo, лог LLM |
| Перевод | googletrans 4.0.0rc1, fallback deep-translator |
| UI | Статический HTML+JS (FastAPI); в планах Electron + React |

Всё работает оффлайн. Интернет нужен **только** для Google Translate
(и позже — для синхронизации правил с dnd.su).

## 📚 Содержание

- [📖 О проекте](#-о-проекте)
- [✨ Возможности](#-возможности)
- [🧰 Технологии](#-технологии)
- [🚀 Быстрый старт](#-быстрый-старт)
- [🧩 Текущий статус](#-текущий-статус)
- [🏛 Архитектура](#-архитектура)
- [🗂 Структура проекта](#-структура-проекта)
- [⚙️ Конфигурация](#️-конфигурация)
- [🔌 API](#-api)
- [🧾 JSON-протокол backend ↔ LLM](#-json-протокол-backend--llm)
- [🗣 Языковая схема](#-языковая-схема)
- [🗄 Схема БД](#-схема-бд)
- [🔁 Game loop](#-game-loop-postapichat)
- [🗺 Дорожная карта](#-дорожная-карта)
- [⚠️ Известные ограничения](#️-известные-ограничения-mvp)
- [📝 Лицензия](#-лицензия)

## 🚀 Быстрый старт

### Предварительные требования

- **Python 3.12+**
- **koboldcpp** с загруженной моделью (порт `5001` по умолчанию)

> Рекомендуемые модели (из ТЗ):
> - **RPBizkitRemiX-v3-12B.i1-Q5_K_M** (основная) — Mistral Nemo 12B, 128K контекста, RP/uncensored, шаблон Alpaca RAW, temperature 0.86–0.92
> - Альтернатива: **MN-Violet-Lotus-12B.Q5_K_M**
>
> ⚠️ Не используйте AttnRes-версии — в koboldcpp они не работают.

### Установка

**1. Клонируйте репозиторий:**

```bash
git clone https://github.com/Caracoto4/DnD-Solo.git
cd DnD-Solo
```

**2. Установите зависимости backend** (один раз):

```powershell
pip install --user -r "dnd-solo/backend/requirements.txt"
```

> ℹ️ `googletrans==4.0.0rc1` жёстко пинает `httpx==0.23.0`, поэтому httpx не указан в `requirements.txt` отдельно — он установится как зависимость googletrans.

**3. Запустите koboldcpp** с моделью (по умолчанию — порт `5001`).

**4. Запустите backend:**

```powershell
cd dnd-solo
run_backend.bat
```

или вручную:

```powershell
cd dnd-solo
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Игра

Откройте **http://127.0.0.1:8000/** — появится форма создания персонажа,
чат с Мастером, панель персонажа, инвентарь, квесты, кубики и кнопки
сохранения.

- 🎮 Игра: **http://127.0.0.1:8000/**
- 📚 Swagger API: **http://127.0.0.1:8000/docs**

Проверка здоровья:

```powershell
curl http://127.0.0.1:8000/api/health
# {"backend": true, "koboldcpp": true, "db": true}
```

## 🧩 Текущий статус

Реализован **MVP-каркас backend + временный веб-интерфейс** (итерация 1 из 3):

| Модуль | Статус |
|---|---|
| State Manager (персонаж, инвентарь, квесты, мир, флаги) | ✅ |
| Dice Roller (`2d6+3`, `1d20+5 adv/dis`, `4d6dl1`) | ✅ |
| Клиент koboldcpp (retry + exponential backoff) | ✅ |
| Prompt Builder (полностью EN, state JSON, история, текст кампании) | ✅ |
| JSON-протокол ответа LLM + валидатор + retry | ✅ |
| Перевод RU↔EN (googletrans + кэш SQLite + fallback) | ✅ |
| Game loop `/api/chat` (перевод → промпт → LLM → парс → state → перевод) | ✅ |
| Проверки навыков (`requested_checks`) — бросает движок | ✅ |
| Save / Load / Undo последнего хода | ✅ |
| Логирование всех LLM-запросов и ответов | ✅ |
| Веб-интерфейс на русском | ✅ (временный) |
| PDF-парсер листа персонажа и кампании | ⬜ итерация 2 |
| RAG по кампании (ChromaDB + embeddings) | ⬜ итерация 2 |
| Полный Rules Engine (резистансии, условия, отдых, level up) | ⬜ итерация 2 |
| Electron + React десктоп-оболочка | ⬜ итерация 3 |
| Парсер правил с dnd.su | ⬜ итерация 3 |

## 🏛 Архитектура

```
Frontend (браузер / Electron) ──► FastAPI (backend/api/routes.py) ──► koboldcpp (LLM)
                                        │
     ┌──────────────┬───────────────────┼──────────────────┬──────────────┐
     │ State Manager│ Prompt Builder    │ LLM Client       │ Translator   │
     │ engine/state │ llm/prompt_builder│ llm/client       │ translate/   │
     │              │ llm/system_prompt │ (retry, backoff) │ translator   │
     ├──────────────┼───────────────────┼──────────────────┼──────────────┤
     │ Dice Roller  │ JSON-протокол     │ Save/Load/Undo   │ SQLite       │
     │ engine/dice  │ llm/parser        │ db/database      │ data/*.db    │
     └──────────────┴───────────────────┴──────────────────┴──────────────┘
```

> **Ключевой принцип:** State Manager — единственный модуль, изменяющий состояние.
> LLM выдаёт запросы на изменение (`state_changes`), движок их валидирует
> (нельзя удалить несуществующий предмет, потратить чужую ячейку и т.д.)
> и применяет. Броски урона по формуле (`"2d6"`) выполняются движком, а не LLM.

## 🗂 Структура проекта

```
DnD-Solo/
├── README.md                      # этот файл
├── dnd-solo/
│   ├── backend/
│   │   ├── engine/
│   │   │   ├── state.py           # State Manager + apply_state_changes
│   │   │   └── dice.py            # парсер формул и броски кубиков
│   │   ├── llm/
│   │   │   ├── client.py          # KoboldClient (async, retry)
│   │   │   ├── prompt_builder.py  # сборка сообщений (EN)
│   │   │   ├── parser.py          # парс + валидация JSON-протокола
│   │   │   └── system_prompt.py   # системный промпт DM (EN)
│   │   ├── translate/
│   │   │   └── translator.py      # googletrans + кэш + fallback
│   │   ├── db/
│   │   │   └── database.py        # схема SQLite, сейвы, undo, логи
│   │   ├── api/
│   │   │   └── routes.py          # все эндпоинты + game loop
│   │   ├── static/
│   │   │   └── index.html         # временный веб-интерфейс (RU)
│   │   ├── tests/
│   │   │   └── test_engine.py     # smoke-тест движка
│   │   ├── main.py                # FastAPI app
│   │   └── requirements.txt
│   ├── config.yaml                # конфигурация
│   ├── run_backend.bat            # запуск backend на Windows
│   ├── docs/ТЗ.md                 # оригинальное техзадание
│   └── data/
│       ├── dnd_solo.db            # SQLite (создаётся автоматически, не коммитится)
│       ├── campaigns/             # PDF кампаний (будущее)
│       ├── saves/                 # (будущее)
│       └── rules/                 # кэш правил 5e_2014 / 5.5e_2024 (будущее)
└── .gitignore
```

## ⚙️ Конфигурация (`dnd-solo/config.yaml`)

| Ключ | По умолчанию | Описание |
|---|---|---|
| `llm.endpoint` | `http://localhost:5001/v1/chat/completions` | Адрес koboldcpp |
| `llm.temperature` | `0.88` | Температура (0.86–0.92 для RP-моделей) |
| `llm.max_tokens` | `1024` | Максимум токенов ответа |
| `llm.json_retries` | `2` | Retry при невалидном JSON |
| `game.rules_edition` | `5e_2014` | Редакция: `5e_2014` или `5.5e_2024` |
| `game.history_max_messages` | `20` | Сколько последних сообщений отдаётся в промпт |
| `translate.enabled` | `true` | Перевод RU↔EN |
| `translate.retries` | `3` | Retry перевода + exponential backoff |
| `server.host` / `server.port` | `127.0.0.1` / `8000` | Адрес backend |

## 🔌 API

| Метод | Путь | Описание |
|---|---|---|
| GET | `/` | Веб-интерфейс игры |
| GET | `/docs` | Swagger UI |
| GET | `/api/health` | Статус backend / koboldcpp / БД |
| POST | `/api/character` | Ручной ввод листа персонажа (сброс сессии) |
| GET | `/api/state` | Текущее состояние игры (компактный JSON) |
| POST | `/api/chat` | Полный ход: `{"message": "действие на русском"}` |
| POST | `/api/roll` | Бросок: `{"formula": "1d20+5 adv"}` |
| POST | `/api/save` | `{"name": "имя"}` — снапшот состояния |
| POST | `/api/load` | `{"name": "имя"}` — загрузка снапшота |
| GET | `/api/saves` | Список сохранений |
| POST | `/api/undo` | Откат состояния на последний ход назад |

Пример ответа `/api/chat`:

```json
{
  "narrative": "Бармен-гном оглядывает вас с ног до головы…",
  "suggested_actions": ["Спросить о недавних путешественниках"],
  "state_changes_applied": ["set_location Oakvale tavern", "set_time evening"],
  "requested_checks": [],
  "check_results": [],
  "state": { "character": {"hp": {"current": 28, "max": 28}}, "location": "Oakvale tavern" }
}
```

## 🧾 JSON-протокол backend ↔ LLM

LLM обязана ответить **строго одним JSON-объектом** (без markdown-фенсов —
парсер их всё же вырезает на случай слабых моделей):

```json
{
  "narrative": "story text for the player (EN)",
  "requested_checks": [
    {"type": "skill", "name": "Perception", "dc": 15, "reason": "search the room"}
  ],
  "state_changes": [
    {"op": "add_item", "target": "player", "item": "Rope", "qty": 1},
    {"op": "damage", "target": "player", "amount": "2d6", "type": "fire"},
    {"op": "set_flag", "key": "found_secret_door", "value": true}
  ],
  "suggested_actions": ["осмотреть стол", "поговорить с NPC"]
}
```

**Валидация** (`backend/llm/parser.py`):
- `narrative` — непустая строка, обязательно;
- `requested_checks[i].type` ∈ `skill | attack | save | initiative | death_save`,
  обязателен числовой `dc`;
- `state_changes[i]` — обязательное поле `op`;
- `suggested_actions` — массив строк (обрезается до 6).

Невалидный ответ → повторный запрос с текстом ошибки (до `llm.json_retries`),
затем ошибка игроку (502).

### Операции `state_changes` (применяет движок `apply_state_changes`)

| op | Поля | Эффект |
|---|---|---|
| `damage` / `heal` | `amount` (формула `"2d6"` или число), `type` | Кубы бросает движок; temp-HP поглощают урон; HP в пределах `[-max, max]` |
| `set_hp_temp` | `value` | Временные HP |
| `add_item` / `remove_item` | `item`, `qty` | Инвентарь; удаление несуществующего/недостаточного — отказ операции |
| `equip_item` | `item`, `value` | Экипировка предмета |
| `set_flag` | `key`, `value` | Флаг мира |
| `add_condition` / `remove_condition` | `condition` | Состояния персонажа (отравлен и т.п.) |
| `add_quest` / `update_quest` | `title`/`details`/`id`/`status` | Журнал квестов |
| `set_location` / `set_time` / `set_weather` | `value` | Локация, время суток, погода |
| `use_spell_slot` | `level` | Расход ячейки заклинания (V1 — счётчики в `flags`) |
| `death_save` / `reset_death_saves` | `success` | Смертельные спасброски |

> `requested_checks` LLM **не бросает сама** — их бросит движок (`1d20` +
> модификатор характеристики + бонус мастерства при владении навыком),
> результат отправляется LLM в следующем запросе и показывается игроку.
> Полный список операций дублирован в системном промпте
> (`backend/llm/system_prompt.py`).

## 🧠 Системный промпт DM

Полный текст — `backend/llm/system_prompt.py`, только EN. Главные правила:

- Ты — DM: нарратив, NPC, мир; числа меняешь **только** через `state_changes`;
- Theater of the Mind: без координат и сетки, позиции абстрактные
  (melee / ranged / cover / out_of_range);
- Всегда отвечать одним строгим JSON по формату протокола;
- Результаты бросков не выдумывать — только из движка;
- Нарратив 2–6 абзацев, на EN (переводится для игрока);
- Персонаж при 0 HP — без сознания и на смертных спасбросках;
- DC по умолчанию: 5 очень легко / 10 легко / 15 сложно / 20 очень сложно.

## 🗣 Языковая схема

```
Игрок (RU) → [googletrans RU→EN] → LLM (EN) → [googletrans EN→RU] → Игрок (RU)
```

- системный промпт и блок состояния — **без перевода** (EN/числа);
- каждый перевод кэшируется в SQLite (`translation_cache`, SHA-256 текста),
  чтобы не упереться в лимит Google;
- retry с exponential backoff, затем fallback на deep-translator,
  затем — оригинал без перевода (игра не встаёт).

## 🗄 Схема БД (SQLite, `data/dnd_solo.db`)

| Таблица | Назначение |
|---|---|
| `translation_cache` | Кэш переводов: `key` (SHA-256) → `text`, языки |
| `saves` | Именованные снапшоты состояния (`snapshot` JSON) |
| `undo_stack` | Последние 50 снапшотов для отката хода |
| `chat_messages` | История чата (EN + RU версии) — готовится к использованию |
| `llm_log` | Все запросы и ответы LLM (отладка и анализ ошибок формата) |

## 🔁 Game loop (`POST /api/chat`)

1. Снапшот состояния в `undo_stack`;
2. Перевод действия игрока RU→EN;
3. Prompt Builder собирает: system + состояние + текст кампании (обрезка
   6000 символов в V1) + последние 20 сообщений истории;
4. Запрос в koboldcpp → парс JSON (retry при ошибке);
5. Валидация и применение `state_changes` движком;
6. Бросок `requested_checks` движком (результат — в историю и в нарратив);
7. Перевод `narrative` и `suggested_actions` EN→RU;
8. Ответ UI, обновление панелей, ход засчитан.

## ⚔️ Режим боя

Без боевой сетки — Theater of the Mind. Позиции абстрактные: ближний бой,
дальний бой, укрытие, вне зоны. Порядок хода списком, инициативу и урон
считает движок. В системном промпте запрещены координаты и точное
позиционирование; при необходимости — уточняющий вопрос игроку.

## 🧪 Тестирование

Smoke-тест движка (без LLM):

```powershell
cd "dnd-solo"
python -m backend.tests.test_engine
# OK: dice + state smoke test passed
```

Покрыто: формулы кубиков (adv/dis/dl), модификаторы характеристик, применение
`state_changes` (включая отказ на удаление несуществующего предмета),
сериализация состояния.

## 🗺 Дорожная карта

### Итерация 2 — правильная механика и PDF
- [ ] Полный Rules Engine: резистансии/иммунитеты, условия с длительностью, короткий/длинный отдых, level up
- [ ] PDF-парсер листа персонажа (fillable forms)
- [ ] PDF кампании → чанкинг текста в контекст
- [ ] Сохранение истории чата в сейвы
- [ ] RAG по кампании (ChromaDB + sentence-transformers)
- [ ] Десктоп-оболочка Electron + React

### Итерация 3 — правила, OCR, голос
- [ ] Парсер правил с dnd.su (Selenium + BeautifulSoup, кэш в `data/rules/`)
- [ ] OCR + LLM-extraction для любых PDF
- [ ] Голосовой ввод/вывод
- [ ] Мультиагентность: отдельный «правиловой» агент валидирует DM

## ⚠️ Известные ограничения MVP

- **Состояние сессии — в памяти процесса.** После рестарта backend персонажа
  нужно заводить заново или грузить из `saves`. История чата в save пока не
  попадает (`history_en` сбрасывается при load).
- Слоты заклинаний — упрощённые счётчики в `flags` (`slots_l1`, `slots_l2`, …).
- Резистансии/иммунитеты к урону не учитываются (TODO V2).
- Соответствие «навык → характеристика» упрощённое
  (`_SKILL_ABIL` в `backend/api/routes.py`); заменит Rules Engine в V2.
- Текст кампании подключается только вручную (`campaign_text` в `GameState`),
  автоматического PDF-парсинга ещё нет.
- Веб-интерфейс — временный (static HTML в `backend/static/index.html`);
  десктоп-оболочка Electron — в итерации 2.

## 📚 Источники правил

Источник правил по ТЗ — [dnd.su](https://dnd.su) (синхронизация по кнопке, будет
в итерации 3). Парсинг сайта выполняется open-source парсером
[Pars_DnD](https://github.com/search?q=Pars_DnD) (Python + Selenium); правила
кэшируются локально в `data/rules/{5e_2014,5.5e_2024}/`. Правила
используются **только** из локального кэша — сайт не парсится на каждом ходу.

## 📝 Лицензия

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<div align="center">
<sub>Made with ⚔️ for solo D&D adventurers · <a href="https://github.com/Caracoto4/DnD-Solo">Caracoto4/DnD-Solo</a></sub>
</div>





