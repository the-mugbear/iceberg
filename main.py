import os
import re
import mmap
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from tqdm import tqdm
from itertools import islice

from dbInit import initDatabase
from patterns_Secrets import secretsPatterns
from patterns_UnsafeFunctions import cppPatterns

# Precompile patterns
compiled_patterns = [re.compile(p) for p in secretsPatterns]
compiled_cpp_patterns = [re.compile(p) for p in cppPatterns]

# Allowed file extensions for filtering
ALLOWED_EXTENSIONS = {".txt", ".cpp", ".py", ".log"}

def dbInsertMatch(conn, pattern, file_path, line_number, content):
    """
    Inserts a match into the matches table in the database.
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO matches (pattern, file_path, line_number, content) VALUES (?, ?, ?, ?)",
        (pattern, file_path, line_number, content)
    )
    conn.commit()

def dbInsertError(conn, file_path, error_message):
    """
    Inserts an error into the errors table in the database.
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO errors (file_path, error_message) VALUES (?, ?)",
        (file_path, error_message)
    )
    conn.commit()

def searchFile(file_path, patterns, cpp_patterns, conn):
    """
    Searches a single file for matches and logs results in the database.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                for line_number, line in enumerate(mmapped_file, start=1):
                    line = line.decode('utf-8', errors='ignore')

                    # Matches for patterns (secrets)
                    for pattern in patterns:
                        if match := pattern.search(line):
                            dbInsertMatch(conn, pattern.pattern, file_path, line_number, match.group(0))

                    # Matches for cpp_patterns (unsafe functions)
                    for cpp_pattern in cpp_patterns:
                        if match := cpp_pattern.search(line):
                            dbInsertMatch(conn, cpp_pattern.pattern, file_path, line_number, match.group(0))
    except Exception as e:
        dbInsertError(conn, file_path, str(e))

def batchIterator(iterable, batch_size):
    """
    Generates batches of files for processing.
    """
    it = iter(iterable)
    while batch := list(islice(it, batch_size)):
        yield batch

def searchDirectory(directory, patterns, cpp_patterns, conn):
    """
    Searches through a directory and logs results in the database.
    """
    file_paths = [
        os.path.join(root, file)
        for root, _, files in os.walk(directory)
        for file in files
        if os.path.splitext(file)[1].lower() in ALLOWED_EXTENSIONS
    ]

    print(f"Number of files to be scanned: {len(file_paths)}")

    # Process files in batches
    batch_size = 1000
    with ThreadPoolExecutor() as executor:
        for batch in tqdm(batchIterator(file_paths, batch_size), total=len(file_paths) // batch_size):
            partial_search = partial(
                searchFile,
                patterns=compiled_patterns,
                cpp_patterns=compiled_cpp_patterns,
                conn=conn,
            )
            executor.map(partial_search, batch)

def main():
    """
    Main entry point for the script.
    """
    directory = input("Enter the directory path to search: ").strip()
    if not os.path.isdir(directory):
        print(f"Error: The provided path is not a valid directory: {directory}")
        return

    conn = initDatabase()  # Initialize database connection
    try:
        searchDirectory(directory, compiled_patterns, compiled_cpp_patterns, conn)
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == '__main__':
    main()
