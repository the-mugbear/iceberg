import sqlite3

def dbInsertMatches(conn, matches):
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO matches (pattern, file_path, line_number, content) VALUES (?, ?, ?, ?)",
        matches
    )
    conn.commit()

def dbInsertErrors(conn, errors):
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO errors (file_path, error_message) VALUES (?, ?)",
        errors
    )
    conn.commit()

def markFileProcessed(conn, file_path):
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO processed_files (file_path) VALUES (?)", (file_path,))
        conn.commit()
    except sqlite3.IntegrityError:
        # File already marked as processed, ignore the error
        pass

def getProcessedFiles(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM processed_files")
    return {row[0] for row in cursor.fetchall()}

def isFileProcessed(conn, file_path):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_files WHERE file_path = ?", (file_path,))
    return cursor.fetchone() is not None
