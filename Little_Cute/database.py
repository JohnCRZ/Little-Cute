import sqlite3

def create_connection():
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect('little_cute.db')
    return conn

def create_tables():
    """Create tables for investments and updates."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY,
            name TEXT,
            platform TEXT,
            amount REAL,
            purchase_date TEXT,
            expiration_date TEXT,
            currency TEXT,
            category TEXT,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS updates (
            id INTEGER PRIMARY KEY,
            investment_id INTEGER,
            update_date TEXT,
            profit_loss REAL,
            FOREIGN KEY(investment_id) REFERENCES investments(id)
        )
    ''')
    conn.commit()
    conn.close()