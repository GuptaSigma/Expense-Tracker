# Expense Tracker

An Expense Tracker web application to record, categorize, and review personal expenses (and optionally income) with a simple dashboard and reporting.

> Repo: `GuptaSigma/Expense-Tracker`

---

## Features

- Add / edit / delete transactions
- Categorize expenses (e.g., Food, Travel, Bills, Shopping)
- View transaction history
- Filter by date range and/or category
- Basic summaries (total spent, totals by category, etc.)
- Responsive UI (works on mobile/desktop)

---

## Tech Stack

- **Backend:** Python (Flask)
- **Server:** WSGI (`wsgi.py`)
- **Config:** `config.py`
- **Dependencies:** `requirements.txt`
- **Deployment:** Render (`render.yaml`)
- **Runtime:** `runtime.txt` / `.python-version`

---

## Project Structure

```text
.
├── app/                # Application package (routes, models, templates, static, etc.)
├── scripts/            # Utility scripts (setup, seed, etc.)
├── config.py           # App configuration (env-based settings)
├── run.py              # Local dev entrypoint
├── wsgi.py             # Production entrypoint for WSGI servers (e.g., gunicorn)
├── requirements.txt    # Python dependencies
├── render.yaml         # Render deployment config
├── runtime.txt         # Runtime version (platform dependent)
└── .python-version     # Local python version (pyenv)
```

---

## Getting Started (Local Development)

### 1) Clone the repository

```bash
git clone https://github.com/GuptaSigma/Expense-Tracker.git
cd Expense-Tracker
```

### 2) Create and activate a virtual environment

**Windows (PowerShell)**
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Configure environment variables

This project typically needs configuration via environment variables (see `config.py`).

Create a `.env` file (optional) or set variables in your shell. Example:

```bash
# Flask
export FLASK_ENV=development
export SECRET_KEY="change-me"

# Database (example)
export DATABASE_URL="sqlite:///expense_tracker.db"
```

> If your project uses a different variable name (e.g., `SQLALCHEMY_DATABASE_URI`), update accordingly.

### 5) Run the app

```bash
python run.py
```

Open your browser at the URL printed in the terminal (commonly `http://127.0.0.1:5000`).

---

## Running in Production

Production typically uses a WSGI server (for example Gunicorn) and the `wsgi.py` entrypoint.

Example (may vary depending on your app factory name inside `wsgi.py`):

```bash
gunicorn wsgi:app
```

If your WSGI variable is named differently (e.g., `application`), use:

```bash
gunicorn wsgi:application
```

---

## Deployment (Render)

This repository includes `render.yaml`, which can be used to deploy on Render with Infrastructure as Code.

General steps:
1. Push code to GitHub
2. In Render, create a new service
3. Choose **Blueprint** and select this repo
4. Configure required environment variables in Render (same ones used locally)
5. Deploy

---

## Common Troubleshooting

### Dependencies won’t install
- Ensure you’re using the Python version specified by `.python-version` / `runtime.txt`.
- Upgrade pip:
```bash
python -m pip install --upgrade pip
```

### App starts but pages error
- Verify required environment variables are set.
- Check database configuration and migrations/initialization steps (if applicable).

---

## Roadmap / Ideas

- Authentication (multi-user support)
- Monthly budget limits + alerts
- Charts (category pie chart, monthly trend line)
- CSV export/import
- Recurring expenses

---

## Contributing

Contributions are welcome:
1. Fork the repo
2. Create a feature branch
3. Commit changes
4. Open a pull request

---

## License

Add a license if you plan to open-source this project (MIT, Apache-2.0, etc.).
