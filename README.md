# Tracker

A voice-powered personal productivity app that turns spoken notes into structured **expenses** and **tasks** — automatically classified by AI.

> Speak it. Track it. Done.

---

## What It Does

Instead of typing entries manually, you **record a voice note** describing an expense or a task. The app transcribes your speech, classifies it using an LLM, and saves it to the right place — all in one step.

**Example voice inputs:**

- *"Spent 200 rupees on lunch at the canteen"* → saved as an **expense** (₹200, Food)
- *"Submit the assignment by Friday, high priority"* → saved as a **task** (deadline: Friday, priority: high)

---

## Features

### Voice Input
- Record audio directly in the browser
- Transcribed using Groq Whisper (`whisper-large-v3-turbo`)
- Classified as expense or task using Groq Llama (`llama-3.3-70b-versatile`)

### Expense Tracking
- View all expenses with date, amount, reason, and category
- Summary stats — today, this week, this month, all time
- Category breakdown (food, transport, shopping, bills, entertainment, health, education, other)
- Last 7 days bar chart
- Filter by time period, category, or search
- Edit and delete entries
- **AI Insights** — on-demand analysis of your last 30 days of spending (patterns, top categories, savings tips)
- **Email insights** — send the AI-generated report to your registered email

### Task Management
- View tasks with deadline, priority, and status
- Summary stats — total, pending, done, overdue
- Calendar view showing tasks per day
- Filter by status (pending, done, overdue) or search
- Toggle task completion, edit, and delete

### Authentication
- Register and login with email/password
- Demo login button for quick access
- Session-based auth with Flask-Login

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask (Python) |
| Database | SQLAlchemy — SQLite (local), PostgreSQL (production) |
| Auth | Flask-Login + bcrypt |
| Speech-to-Text | Groq Whisper API |
| Classification & Insights | Groq Llama 3.3 70B |
| Email | SMTP (Gmail or any provider) |
| Frontend | Jinja2 templates, vanilla JS |

---

## Getting Started

### Prerequisites

- Python 3.10+
- A [Groq API key](https://console.groq.com)

### Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd Tracker

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
```

Edit `.env` with your values:

```
GROQ_API_KEY=gsk_your_key_here
SECRET_KEY=change-me-to-a-random-string
DATABASE_URL=postgresql://user:password@host:5432/dbname
FLASK_DEBUG=true

# Optional — for emailing insights
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=your-email@gmail.com
```

> For local development, you can leave `DATABASE_URL` unset — it defaults to SQLite.
> The SMTP variables are optional — the insights feature works without them, but the "Email" button requires a configured SMTP provider. For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833).

### Run

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## Deployment

The app is configured for **Vercel** serverless deployment. Just push to your repo with `vercel.json` in place and set the environment variables in the Vercel dashboard.

---

## Project Structure

```
Tracker/
├── app.py              # Flask app — routes, auth, API endpoints
├── models.py           # Database models (User, Expense, Task)
├── model.py            # AI classification + insights logic (Groq LLM)
├── record.py           # Speech-to-text (Groq Whisper)
├── api/
│   └── index.py        # Vercel serverless entry point
├── templates/
│   ├── base.html       # Shared layout and navigation
│   ├── login.html      # Login page
│   ├── register.html   # Registration page
│   ├── home.html       # Voice recording interface
│   ├── expenses.html   # Expense dashboard
│   └── tracker.html    # Task dashboard
├── requirements.txt
├── .env.example
└── vercel.json
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | API key for Groq (Whisper + Llama) |
| `SECRET_KEY` | Flask session secret |
| `DATABASE_URL` | PostgreSQL connection string (optional — defaults to SQLite) |
| `FLASK_DEBUG` | Set to `true` for development |
| `SMTP_HOST` | SMTP server hostname (optional — for email insights) |
| `SMTP_PORT` | SMTP port, default `587` (optional) |
| `SMTP_USER` | SMTP login username/email (optional) |
| `SMTP_PASS` | SMTP login password / app password (optional) |
| `SMTP_FROM` | Sender email address (optional — defaults to `SMTP_USER`) |

---

## License

This project is for personal use.
