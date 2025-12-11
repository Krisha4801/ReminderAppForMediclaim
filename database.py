import sqlite3

def get_db():
    connection = sqlite3.connect("policy.db")
    connection.row_factory = sqlite3.Row
    return connection

def create_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS policy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            amount REAL,
            policy_number TEXT,
            start_date TEXT,
            end_date TEXT,
            policy_type TEXT
        );
            
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            message TEXT,
            next_try TEXT,
            status TEXT
        );
    """)
    conn.commit()
    conn.close()

create_table()
