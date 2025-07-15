import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                month TEXT,
                category TEXT,
                amount REAL,
                UNIQUE(user_id, month, category)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                month TEXT,
                category TEXT,
                amount REAL,
                timestamp TEXT
            )
        """)

def create_user(email, hashed_password):
    with get_connection() as conn:
        try:
            conn.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
            return True
        except sqlite3.IntegrityError:
            return False

def authenticate_user(email, password_plain):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            import bcrypt
            if bcrypt.checkpw(password_plain.encode(), row["password"].encode()):
                return row
        return None

def get_user_id(email):
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        return row["id"] if row else None

def save_budget(user_id, month, category, amount):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO budgets (user_id, month, category, amount)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, month, category)
            DO UPDATE SET amount = excluded.amount
        """, (user_id, month, category, amount))

def get_budget(user_id, month):
    with get_connection() as conn:
        return conn.execute("""
            SELECT category, amount FROM budgets
            WHERE user_id = ? AND month = ?
        """, (user_id, month)).fetchall()

def add_expense(user_id, month, category, amount):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO expenses (user_id, month, category, amount, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, month, category, amount, datetime.now().isoformat()))

def get_expenses(user_id, month):
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, category, amount, timestamp FROM expenses
            WHERE user_id = ? AND month = ?
            ORDER BY timestamp DESC
        """, (user_id, month)).fetchall()

def update_expense(expense_id, new_amount):
    with get_connection() as conn:
        conn.execute("""
            UPDATE expenses SET amount = ? WHERE id = ?
        """, (new_amount, expense_id))

def delete_expense(expense_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
