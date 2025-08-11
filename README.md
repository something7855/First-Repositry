# Voice Assistant (Flask + MySQL)

A simple voice-based AI assistant with Flask backend, MySQL storage, and a browser frontend using the Web Speech and SpeechSynthesis APIs. Stores all conversations in MySQL and can optionally use OpenAI for GPT-style responses.

## Features
- Start/stop microphone to capture voice (Web Speech API)
- Live transcript display
- Sends text to Flask backend via fetch
- Stores user input and assistant reply in MySQL
- Shows last 10 messages (auto-refresh after each interaction)
- Speaks assistant reply aloud (SpeechSynthesis)
- Optional: GPT responses if `OPENAI_API_KEY` is set (fallback to rule-based + Wikipedia)

## Tech
- Python 3.x, Flask
- MySQL (local)
- `mysql-connector-python`, `wikipedia`, optional `openai`

## Database Setup
1. Ensure MySQL is running locally and you know your root password (empty by default per spec).
2. Create the database and table:
   ```bash
   mysql -u root -p < sql/create_learningproject.sql
   ```
   If your root password is empty, press Enter when prompted.

## App Setup
1. Clone or copy this project.
2. Create and activate a virtual environment (recommended):
   ```bash
   cd /workspace
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment (optional):
   - Copy `.env.example` to `.env` and edit if needed (DB creds, `OPENAI_API_KEY`).

## Run the App
Using Flask's dev server:
```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```
Open `http://127.0.0.1:5000/` in your browser.

Alternatively, run directly:
```bash
python app.py
```

## Notes
- If the Web Speech API is not supported in your browser, try Chrome.
- Without `OPENAI_API_KEY`, the assistant uses rule-based replies and Wikipedia summaries.
- Data is stored in the `conversations` table (`LearningProject` DB).

## Troubleshooting
- MySQL connection errors: verify credentials in `.env` and ensure the DB/table exist.
- Port conflicts on 5000: set `FLASK_RUN_PORT` or run `python app.py` and change the port in code.
- SSL or CORS is not required for localhost; for production, add proper config.