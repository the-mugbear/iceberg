import sqlite3

def initDatabase(db_path="results.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create matches table with a timestamp
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT NOT NULL,
            file_path TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create errors table with a timestamp
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            error_message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    return conn
