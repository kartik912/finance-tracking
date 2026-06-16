"""Run this script once to create the SQLite database and all tables.

Usage:
    python create_db.py
"""
from __future__ import annotations

import os

from config.database import create_tables, init_db

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "database", "finance.db"
)


def main() -> None:
    print(f"Creating database at: {DB_PATH}")
    init_db(DB_PATH)
    create_tables()
    print("All tables created successfully.")


if __name__ == "__main__":
    main()
