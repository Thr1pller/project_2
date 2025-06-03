import sqlite3

def initialize_database(db_path: str = "library.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS books (
        isbn TEXT PRIMARY KEY,
        title TEXT,
        author TEXT,
        year INTEGER,
        genre TEXT,
        available INTEGER,
        issued_to TEXT,
        issue_date TEXT,
        times_issued INTEGER
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        email TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS issued_books (
        user_id TEXT,
        isbn TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(isbn) REFERENCES books(isbn)
    )
    """)

    conn.commit()
    conn.close()