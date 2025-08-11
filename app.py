import os
import datetime
from typing import List, Dict, Optional

from flask import Flask, render_template, request, jsonify
import mysql.connector
from mysql.connector import Error as MySQLError
import wikipedia

# Optional OpenAI integration
OPENAI_ENABLED = False
try:
    from openai import OpenAI  # type: ignore
    OPENAI_ENABLED = True
except Exception:
    OPENAI_ENABLED = False

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Database configuration with provided defaults
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "LearningProject"),
}

wikipedia.set_lang("en")


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def ensure_table_exists() -> None:
    """Create the conversations table if it doesn't already exist."""
    ddl = (
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_input TEXT,
            assistant_reply TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(ddl)
        conn.commit()
    except MySQLError as e:
        # Log to console; in production use proper logging
        print(f"[DB] Failed to ensure table exists: {e}")
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def fetch_last_messages(limit: int = 10) -> List[Dict]:
    rows: List[Dict] = []
    query = (
        "SELECT id, user_input, assistant_reply, timestamp FROM conversations "
        "ORDER BY timestamp DESC, id DESC LIMIT %s"
    )
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (limit,))
        for rid, user_input, assistant_reply, ts in cur.fetchall():
            rows.append(
                {
                    "id": rid,
                    "user_input": user_input or "",
                    "assistant_reply": assistant_reply or "",
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "",
                }
            )
    except MySQLError as e:
        print(f"[DB] Failed to fetch messages: {e}")
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    # Return in chronological order (oldest first)
    return list(reversed(rows))


def store_conversation(user_text: str, reply_text: str) -> None:
    insert_sql = (
        "INSERT INTO conversations (user_input, assistant_reply) VALUES (%s, %s)"
    )
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(insert_sql, (user_text, reply_text))
        conn.commit()
    except MySQLError as e:
        print(f"[DB] Failed to store conversation: {e}")
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def generate_rule_based_reply(user_text: str) -> str:
    text = (user_text or "").strip().lower()
    if not text:
        return "I didn't catch that. Please say something."

    # Greetings
    greetings = ["hi", "hello", "hey", "good morning", "good evening", "good afternoon"]
    if any(text.startswith(greet) for greet in greetings) or any(g in text for g in greetings):
        return "Hello! How can I assist you today?"

    # Time / Date
    if "time" in text:
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {now}."
    if "date" in text or "today" in text:
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {today}."

    # Weather placeholder
    if "weather" in text:
        return (
            "I can't fetch live weather without an API, but you can ask something like "
            "'What's the weather in London?' and I will add that in the future."
        )

    # Wikipedia search: handle 'who is', 'what is', or 'tell me about'
    triggers = ["who is", "what is", "tell me about", "define", "explain"]
    if any(trig in text for trig in triggers):
        # Extract query heuristically
        query = text
        for trig in triggers:
            if trig in query:
                query = query.replace(trig, "")
        query = query.strip(" ?!.,:")
        if not query:
            # fallback: try using original text without triggers logic
            query = user_text.strip()
        try:
            summary = wikipedia.summary(query, sentences=2, auto_suggest=True, redirect=True)
            return summary
        except wikipedia.DisambiguationError as e:
            option = e.options[0] if e.options else ""
            if option:
                try:
                    summary = wikipedia.summary(option, sentences=2)
                    return summary
                except Exception:
                    pass
            return (
                "That topic has multiple meanings. Please be more specific, for example: "
                f"'{e.options[:3] if hasattr(e, 'options') else '...'}'"
            )
        except wikipedia.PageError:
            return "I couldn't find information on that topic. Try rephrasing."
        except Exception:
            return "Sorry, I ran into a problem fetching information from Wikipedia."

    # Default fallback
    return (
        "I'm here to help. You can ask about the date, time, or say 'tell me about <topic>' "
        "for a quick Wikipedia summary."
    )


def generate_ai_reply(user_text: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not (OPENAI_ENABLED and api_key):
        return generate_rule_based_reply(user_text)

    try:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise, helpful voice assistant. Keep responses under 120 words unless asked for detail.",
                },
                {"role": "user", "content": user_text},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        reply = completion.choices[0].message.content or ""
        return reply.strip() or generate_rule_based_reply(user_text)
    except Exception as e:
        print(f"[AI] OpenAI error: {e}")
        return generate_rule_based_reply(user_text)


@app.route("/")
def index():
    ensure_table_exists()
    return render_template("index.html")


@app.route("/history", methods=["GET"])
def history():
    messages = fetch_last_messages(limit=10)
    return jsonify({"messages": messages})


@app.route("/process", methods=["POST"])
def process_text():
    try:
        data = request.get_json(silent=True) or {}
        user_text: str = (data.get("text") or "").strip()
        if not user_text:
            return jsonify({"error": "No text provided."}), 400

        reply_text: str = generate_ai_reply(user_text)
        store_conversation(user_text, reply_text)

        return jsonify({"reply": reply_text})
    except Exception as e:
        print(f"[Server] Error in /process: {e}")
        return jsonify({"error": "Internal server error."}), 500


if __name__ == "__main__":
    # For debugging locally via `python app.py`
    app.run(host="127.0.0.1", port=5000, debug=True)