import sqlite3
from werkzeug.security import generate_password_hash


def get_db():
    conn = sqlite3.connect("spendly.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def get_expenses_for_user(conn, user_id, date_from="", date_to=""):
    query = "SELECT id, date, category, description, amount FROM expenses WHERE user_id = ?"
    params = [user_id]
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    query += " ORDER BY date DESC, id DESC"
    return conn.execute(query, params).fetchall()


def seed_db():
    conn = get_db()
    cursor = conn.cursor()

    count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count > 0:
        conn.close()
        return

    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    expenses = [
        (user_id, 12.50,  "Food",          "2026-04-01", "Lunch at cafe"),
        (user_id, 45.00,  "Transport",     "2026-04-03", "Monthly bus pass"),
        (user_id, 120.00, "Bills",         "2026-04-05", "Electricity bill"),
        (user_id, 30.00,  "Health",        "2026-04-07", "Pharmacy"),
        (user_id, 18.99,  "Entertainment", "2026-04-09", "Streaming subscription"),
        (user_id, 65.40,  "Shopping",      "2026-04-11", "Clothes"),
        (user_id, 9.75,   "Other",         "2026-04-13", "Miscellaneous"),
        (user_id, 22.00,  "Food",          "2026-04-14", "Groceries"),
    ]

    cursor.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )

    conn.commit()
    conn.close()
