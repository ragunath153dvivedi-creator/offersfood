# Telegram Ticket Bot System

A complete ticket management system with a Telegram bot frontend, Django REST backend, and React agent panel.

## Architecture

```
┌────────────────────┐     ┌──────────────────────┐     ┌────────────────────┐
│   Telegram User    │────▶│   Telegram Bot        │────▶│   Django Backend   │
│   (Customer)       │◀────│   (python-telegram-bot)│◀────│   (DRF + Channels) │
└────────────────────┘     └──────────────────────┘     └─────────┬──────────┘
                                                                   │
                                                           WebSocket│REST API
                                                                   │
                                                        ┌──────────▼──────────┐
                                                        │   React Agent Panel  │
                                                        │   (Vite + Tailwind)  │
                                                        └─────────────────────┘
```

## Features

### Telegram Bot
- **10 service categories**: Flights, Hotels, Stays, Food, Tickets, Movies, Shopping, Rentals, Rides, Bill Payments
- **Dynamic company selection** under each service
- **Dynamic form builder** — each company has its own form schema (JSON config, zero code changes to add new ones)
- **Live chat relay** — once an agent picks up, user chats directly with the agent through the bot
- **Bot failover** — multiple bot tokens, automatic health checks, standby bot promotion

### Agent Panel
- **Role-based access**: Super Admin sees everything, Agents only see their allowed services
- **Real-time updates** via WebSocket — new tickets, messages appear instantly
- **Ticket lifecycle**: Open → Assigned → In Progress → On Hold → Resolved → Closed
- **Ticket pickup** with race condition protection (`SELECT FOR UPDATE`)
- **Transfer tickets** between agents (only assigned agent or super admin can transfer)
- **Live chat** with customers through the panel
- **Internal notes** — agent-only messages not sent to customers
- **Dashboard** with stats and quick access to open tickets

### Super Admin Powers
- Create/disable agents
- Assign services to agents
- View all tickets and chats (including user PII that agents can't see)
- Manage services, companies, and form schemas
- Bot configuration and health monitoring
- Set concurrent ticket limits per agent

### Bot Failover System
- Health monitor daemon checks each bot every 2 minutes
- If active bot goes down → automatically promotes next standby bot
- Bots have priority ordering for promotion
- Recovers previously failed bots back to standby when they come back online

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — add your TELEGRAM_BOT_TOKENS

# 2. Start everything
docker-compose up --build

# 3. Access
# Agent Panel: http://localhost:5173
# Backend API: http://localhost:8000/api/
# Django Admin: http://localhost:8000/admin/
# Login: admin / admin123456
```

### Option 2: Manual Setup

#### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (or SQLite for dev)
- Redis

#### Backend

```bash
cd backend

# Create virtualenv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp ../.env.example .env
# Edit .env with your values

# Database setup
python manage.py migrate
python manage.py setup_superadmin
python manage.py seed_services

# Run the server (use daphne for WebSocket support)
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

#### Telegram Bot

```bash
cd backend

# Set your bot token
export TELEGRAM_BOT_TOKENS=your_bot_token_here
export BACKEND_URL=http://localhost:8000
export BOT_INTERNAL_KEY=bot-internal-secret

# Run the bot (polling mode for development)
python bot/telegram_bot.py
```

#### Health Monitor (Optional, for failover)

```bash
cd backend
python bot/health_monitor.py
```

#### Frontend

```bash
cd frontend

npm install
npm run dev
# Opens at http://localhost:5173
```

---

## Setting Up Telegram Bots

### 1. Create Bot(s) with BotFather

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Choose a name and username
4. Save the token
5. Repeat for backup bots (recommended: 2-3 bots)

### 2. Configure Tokens

**For development (polling mode):**
```env
TELEGRAM_BOT_TOKENS=token1,token2,token3
```

**For production (webhook mode):**
```env
TELEGRAM_BOT_TOKENS=token1,token2,token3
TELEGRAM_WEBHOOK_URL=https://yourdomain.com
```

### 3. Register Bots in Admin Panel

1. Login to the Agent Panel as Super Admin
2. Go to Bot Config
3. Add each bot with its token via Django Admin (`/admin/`)
4. Set priority order (0 = highest priority)
5. Run health check to verify

---

## Adding New Services & Companies

### Via Django Admin
Go to `/admin/` → Services / Companies

### Via Agent Panel
Login as Super Admin → Services → Add Service / Add Company

### Via Seed Command
Edit `backend/core/management/commands/seed_services.py` and add your data, then run:
```bash
python manage.py seed_services
```

### Form Schema Format

Each company has a `form_schema` JSON array that defines what to ask users:

```json
[
  {"key": "from_city", "label": "From which city?", "type": "text", "required": true},
  {"key": "passengers", "label": "Number of passengers?", "type": "number", "required": true},
  {"key": "class", "label": "Class?", "type": "choice", "options": ["Economy", "Business"], "required": true},
  {"key": "notes", "label": "Any special requirements?", "type": "text", "required": false}
]
```

**Supported field types:** `text`, `number`, `date`, `email`, `phone`, `choice`

---

## API Endpoints

### Auth
- `POST /api/auth/login/` — Login, returns JWT tokens
- `POST /api/auth/logout/` — Logout
- `GET /api/auth/me/` — Current user info

### Tickets
- `GET /api/tickets/` — List tickets (filtered by agent's allowed services)
- `GET /api/tickets/{id}/` — Ticket detail
- `POST /api/tickets/{id}/pick/` — Pick up an open ticket
- `POST /api/tickets/{id}/transfer/` — Transfer to another agent
- `POST /api/tickets/{id}/change_status/` — Change status

### Messages
- `GET /api/tickets/{id}/messages/` — List messages
- `POST /api/tickets/{id}/messages/` — Send message (auto-relayed to Telegram)

### Users (Super Admin)
- `GET /api/users/` — List agents
- `POST /api/users/` — Create agent
- `PATCH /api/users/{id}/` — Update agent
- `POST /api/users/{id}/toggle_active/` — Enable/disable agent

### Services & Companies (Super Admin for writes)
- `GET /api/services/` — List services
- `POST /api/services/` — Create service
- `GET /api/companies/` — List companies
- `POST /api/companies/` — Create company

### Bot Config (Super Admin)
- `GET /api/bots/` — List bot configurations
- `POST /api/bots/{id}/activate/` — Set as active bot
- `POST /api/bots/{id}/health_check/` — Manual health check

### WebSocket
- `ws://host/ws/agent/?token=JWT` — Agent real-time updates

---

## Production Deployment

### Railway (Your usual stack)

**Backend:**
```bash
# Set build command
pip install -r requirements.txt

# Set start command
python manage.py migrate && python manage.py seed_services && daphne -b 0.0.0.0 -p $PORT config.asgi:application
```

**Bot process** (separate Railway service):
```bash
python bot/telegram_bot.py
```

**Health Monitor** (separate Railway service):
```bash
python bot/health_monitor.py
```

**Frontend**: Deploy to Vercel/Netlify with API proxy to Railway.

### Environment Variables for Production
```env
SECRET_KEY=<generate-a-strong-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgres://...
REDIS_URL=redis://...
TELEGRAM_BOT_TOKENS=token1,token2
TELEGRAM_WEBHOOK_URL=https://yourdomain.com
BOT_INTERNAL_KEY=<generate-a-strong-key>
CORS_ORIGINS=https://panel.yourdomain.com
```

---

## Project Structure

```
ticket-bot/
├── backend/
│   ├── config/              # Django settings, URLs, ASGI
│   ├── core/                # Main app
│   │   ├── models.py        # User, Service, Company, Ticket, Message, BotConfig
│   │   ├── views.py         # REST API views
│   │   ├── serializers.py   # DRF serializers
│   │   ├── consumers.py     # WebSocket consumers
│   │   ├── permissions.py   # Role-based permissions
│   │   ├── middleware.py     # JWT WebSocket auth
│   │   ├── routing.py       # WebSocket routing
│   │   └── management/commands/
│   │       ├── seed_services.py     # Seed services data
│   │       └── setup_superadmin.py  # Create initial admin
│   ├── bot/
│   │   ├── telegram_bot.py   # Main bot with conversation handlers
│   │   └── health_monitor.py # Failover health checker
│   └── manage.py
├── frontend/
│   └── src/
│       ├── components/Layout.jsx
│       ├── hooks/useAuth.jsx, useWebSocket.js
│       ├── pages/            # Login, Dashboard, Tickets, Agents, Services, BotConfig
│       └── utils/api.js      # API client
├── docker-compose.yml
├── requirements.txt
└── README.md
```
