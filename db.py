# db.py
import sqlite3
import os
from typing import List, Tuple

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "expenses.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

def add_expense(amount: float, category: str, date: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO expenses (amount, category, date) VALUES (?, ?, ?)",
                (amount, category, date))
    conn.commit()
    conn.close()

def get_expenses() -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, amount, category, date FROM expenses ORDER BY date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def clear_all():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Delete all rows
    cur.execute("DELETE FROM expenses")

    # Reset AUTOINCREMENT counter so new IDs start from 1
    cur.execute("DELETE FROM sqlite_sequence WHERE name='expenses'")

    conn.commit()
    conn.close()
