# Chess for Kids - Technical Documentation

**Version 1.0** | Built with Python Flask + SQLAlchemy + Canvas API  
Educational chess platform for children with guided lessons, adaptive AI opponents, and a web UI translated into Bulgarian.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Setup & Installation](#setup--installation)
5. [Project Structure](#project-structure)
6. [Database Schema](#database-schema)
7. [API Endpoints](#api-endpoints)
8. [Frontend Implementation](#frontend-implementation)
9. [AI Engine](#ai-engine)
10. [Features](#features)
11. [Development Guidelines](#development-guidelines)
12. [Deployment](#deployment)
13. [Troubleshooting](#troubleshooting)
14. [License & Credits](#license--credits)

---

## Project Overview

Chess for Kids помага на деца между 6 и 12 години да научат шаха чрез:

- **User Management**: Регистрация, вход, профил с тема на дъската и списък с приятели.
- **Single & Multiplayer**: Игра срещу AI (Easy/Medium/Hard) или срещу приятел по потребителско име.
- **Education**: Шест урока, примери и мини задачи.
- **History**: Пълен списък с партии, таймери, захванати фигури и възможност за възобновяване на `finished` партии.
- **Customization**: Три борд теми, звукови ефекти, контрол на времето (bullet, blitz, rapid, classical, unlimited).

---

## Architecture

```
┌──────────────────────────┐
│        Browser           │
│  HTML/CSS + Canvas + JS  │
└─────────────┬────────────┘
              │ HTTP/JSON
┌─────────────▼────────────┐
│      Flask App Server    │
│  Blueprints: auth/main/game
│  python-chess validation
│  SimpleChessAI (Easy/Medium/Hard)
└─────────────┬────────────┘
              │ SQLAlchemy ORM
┌─────────────▼────────────┐
│       SQLite (chess.db)  │
│  user, friend, friend_request
│  game, lesson tables     │
└──────────────────────────┘
```

Data flow за ход:
1. Потребител кликва върху поле → `ChessGame.handleSquareSelection()` валидира и изпраща `/game/<id>/move`.
2. `game.make_move` проверява хода чрез python-chess, записва PGN, обновява FEN и ако е single-player избира AI ход.
3. Отговорът съдържа FEN, SAN списък, захванати фигури, таймер snapshot и статус (`active`, `won`, `lost`, `draw`, `finished`).
4. Frontend обновява локалната карта на фигурите, таймерите и индикатора за ход.

---

## Technology Stack

| Component        | Technology      | Version |
|------------------|-----------------|---------|
| Language         | Python          | 3.11+ (project uses 3.14 locally) |
| Web Framework    | Flask           | 2.3.x   |
| ORM              | SQLAlchemy      | 1.4.x   |
| Auth             | Flask-Login     | 0.6.x   |
| Forms            | Flask-WTF/WTForms | 1.1 / 3.0 |
| Chess Engine     | python-chess    | 1.9.x   |
| Frontend         | HTML5, CSS3, Vanilla JS (Canvas + DOM overlays) |
| DB               | SQLite          | bundled |

Key Python dependencies (see `requirements.txt`).

---

## Setup & Installation

### Prerequisites
- Python 3.8+
- `pip`
- (Optional) virtual environment

### Steps
1. **Clone / open project**
   ```bash
   cd d:\WORK\Chess
   ```
2. **Create virtualenv**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Prepare database**
   ```bash
   python add_columns.py
   ```
5. **Run dev server**
   ```bash
   python run.py  # http://127.0.0.1:5000
   ```

---

## Project Structure

```
Chess/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── main.py
│   │   └── game.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── about.html, lessons.html, profile.html
│   │   ├── auth/login.html, auth/register.html
│   │   └── game/new.html, game/play.html
│   └── static/
│       ├── css/style.css
│       ├── js/{main.js, utils.js, chess.js, game.js}
│       └── img/pieces/*.svg
├── run.py
├── requirements.txt
├── add_columns.py
└── TECHNICAL_README.md
```

---

## Database Schema

### `user`
- `id` (PK), `username` (unique), `email` (unique)
- `password_hash`, `created_at`, `board_theme`

### `game`
- `id`, `player_id`, `opponent_id`
- `player_color`, `difficulty`, `fen`, `pgn`
- `status` (`active`,`won`,`lost`,`draw`,`finished`)
- `time_control`, `white_moves`, `black_moves`
- `white_time_left/spent`, `black_time_left/spent`, `game_duration_seconds`
- `white_score`, `black_score`, `redo_stack`

### `lesson`
- `id`, `title`, `description`, `content`, `order`

### `friend`
- `id`, `user_id`, `friend_id`, `created_at`

### `friend_request`
- `id`, `sender_id`, `receiver_id`
- `status` (`pending`, `accepted`, `declined`)
- `created_at`, `responded_at`

---

## API Endpoints

### Auth (`/auth`)
- `POST /auth/register`: username/email/password, optional board theme. Validates lengths, uniqueness.
- `POST /auth/login`: username + password. Sets Flask-Login session.
- `GET /auth/logout`: clears session.

### Game (`/game`)
- `GET /game/new`: форма за настройка.
- `POST /game/new`: създава запис в `game` със стартов FEN и таймери.
- `GET /game/<id>`: рендерира `play.html` (достъпно само за участниците).
- `GET /game/<id>/board`: JSON с FEN, SAN, законни ходове, таймер snapshot, точки от захванати фигури, redo наличност.
- `POST /game/<id>/move`: `{move, time_snapshot}`. Валидира, записва PGN, пуска AI, обновява статус/таймери, връща нов state + `ai_move` и `ai_delay_ms` за симулация.
- `POST /game/<id>/undo`: само single-player. Ролбек на последните два хода, обновява redo stack.
- `POST /game/<id>/redo`: reapply последния stack entry.
- `POST /game/<id>/leave`: `{time_snapshot}` по желание. Маркира статуса като `finished` и запазва таймерите.
- `POST /game/<id>/resume`: връща state като `/board` и сменя статуса обратно на `active` (ако е бил `finished`).
- `POST /game/<id>/resign`: optional `{time_snapshot}` и задава `won/lost` според това кой се е предал.

### Main (`/`)
- `GET /`: новият home layout (hero, features, CTA).
- `GET /about`, `GET /lessons`: статични страници.
- `GET /profile`: показва тема на дъската, приятели, входящи/изходящи покани, статистика и история с филтри/пагинация.
- `POST /profile`: обработва действия чрез `action` параметър (`send_request`, `accept_request`, `decline_request`, `cancel_request`, `dismiss_request`, `update_theme`, `update_email`, `update_password`).

---

## Frontend Implementation

### Board & Canvas (`app/static/js/chess.js`)
- Единствен клас `ChessGame` управлява рендеринг, логика и таймери.
- Поддържа локално преместване (вкл. рокада и en passant) преди сървърният отговор.
- `applyServerPayload` синхронизира FEN, SAN, таймери и индикатора за ход.
- Таймерите използват един `setInterval`, спират се при `finished/won/lost/draw` и snapshot-ите се изпращат при всеки POST.
- Звуците и анимациите се контролират през `AudioManager`/`NotificationManager` (в `utils.js`).

### Game bootstrap (`app/static/js/game.js`)
- Инициализира `ChessGame`, свързва Undo/Redo/Resign/New/Resume и управлява leave модала.
- `beforeunload` използва `navigator.sendBeacon` за изпращане на `/leave` дори при затворен таб.

### Profile UI (`app/templates/profile.html` + `app/routes/main.py`)
- Карти за тема/акаунт/приятели и форми за покани.
- Incoming/outgoing request списъци с бутони Accept/Decline/Cancel/Dismiss.
- Историята има цветни редове, филтри „пилички“, пагинация и бутон „Възобнови“ за single-player `finished` партии.

### Styling (`app/static/css/style.css`)
- Обновена навигация/герой, `.requests-grid`, `.filter-pill`, `.history-actions`, `.lesson-grid`, `.btn-small`, `.status-chip`.
- Responsive grid layout + общи бутони (`.btn-full`, `.btn-large`).

---

## AI Engine

SimpleChessAI (`app/routes/game.py`):
- **Easy**: произволен законен ход, 0.4–0.9 s забавяне.
- **Medium**: евристика (captures/checks/center/development) + 0.8–1.4 s забавяне.
- **Hard**: Negamax + alpha-beta (3 plies) със стойности P=100, N=320, B=330, R=500, Q=900 и бонуси за център/king safety (1.2–1.8 s забавяне).
- Ограничения: няма opening book, няма iterative deepening, redo stack се нулира след нов ход.

---

## Features

### ✅ Implemented
1. **User Management** – пълна регистрация/вход, профил с избор на тема, списък и заявки за приятели.
2. **Game Modes** – AI (3 нива) и покана към приятел; контроли на времето (вкл. unlimited и добавки).
3. **Gameplay** – python-chess валидация, undo/redo, SAN списък, точкуване на захванати фигури, redo stack, snapshot таймери.
4. **UI/UX** – Canvas борд, индикатор за ход, симулирано мислене на AI, leave/resume поток, локализация на целия интерфейс, история с филтри и пагинация.
5. **Education** – отделна страница с 6 урока + about секция.
6. **Statistics** – win/loss/draw, `finished` статус за запазени партии, история с време и материално предимство.

### 🚀 Future Enhancements
- Real-time multiplayer (Flask-SocketIO)
- Сървърно следене на таймерите и автоматични загуби при time-out
- По-силен AI (по-дълбок minimax, transposition tables, външен движок)
- Opening book / endgame tablebases
- Leaderboards (Elo / glicko-2)
- Ежедневни задачки (puzzles)
- Mobile app (React Native / Flutter)
- Speech integration за произнасяне на ходовете

---

## Development Guidelines

### Adding a Route
```python
@main_bp.route('/newpage')
@login_required
def new_page():
    return render_template('newpage.html', data=...)
```

### Adding a Model
```python
class MyModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    data = db.Column(db.String(255))
```
Run `python add_columns.py` after schema changes (no Alembic migrations).

### Templates & CSS
- Templates extend `base.html` и използват Jinja блокове.
- CSS се управлява чрез `app/static/css/style.css` (mobile-first breakpoints ~768px).

### JS Debugging
- DevTools console, Network за API, Canvas overlay за визуализация на кликвания.

---

## Deployment

- **Dev**: `python run.py` (Flask debug)
- **Production**: `gunicorn -w 4 -b 0.0.0.0:8000 run:app`
- **Env vars**: `FLASK_ENV`, `SECRET_KEY`, `DATABASE_URL`
- **Docker**: Python 3.11 base image, copy app, install reqs, expose 5000, run `python run.py` или `gunicorn`.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 404 on `/game/new` | Увери се, че `game_bp` е регистриран в `app/__init__.py`. |
| Pieces missing | Проверка в DevTools -> Network за SVG файловете (`/static/img/pieces`). |
| "No moves to undo" | Очаквано при липса на записани ходове; undo работи само срещу AI. |
| Timer stuck | Проверете дали snapshot-ите се изпращат; някои браузъри блокират `setInterval`. |
| Database locked | Затворете други процеси, изтрийте `chess.db`, стартирайте `python add_columns.py`. |
| Module not found | Активирай виртуалната среда и `pip install -r requirements.txt`. |

---

## License & Credits

Chess for Kids е създаден за образователни цели.  
Piece SVGs – Wikimedia Commons.  
Визията е вдъхновена от chess.com и lichess.org.

---

**Last Updated**: November 15, 2025  
**Version**: 1.0  
**Python**: 3.14  
**Flask**: 2.3.3
