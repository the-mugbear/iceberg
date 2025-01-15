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

# Tweak depending on hardware (tested at 1000 just fine on poorly allocated VM)
# batch_size = 2000
# Found this suggestion online, unsure so we full send
batch_size = max(1000, os.cpu_count() * 500)

# TODO: Testing batch insert rather than individual inserts to speed up execution
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


def searchFile(file_path, patterns, cpp_patterns, conn, batch_size=100):
    matches = []
    errors = []
    try:
        with open(file_path, 'rb') as file:
            try:
                with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                    for line_number, line in enumerate(mmapped_file, start=1):
                        line = line.decode('utf-8', errors='ignore')
                        for pattern in patterns:
                            if match := pattern.search(line):
                                matches.append((pattern.pattern, file_path, line_number, match.group(0)))
                                if len(matches) >= batch_size:
                                    dbInsertMatches(conn, matches)
                                    matches.clear()

                        # Uncomment to enable unsafe function detection
                        # for cpp_pattern in cpp_patterns:
                        #     if match := cpp_pattern.search(line):
                        #         matches.append((cpp_pattern.pattern, file_path, line_number, match.group(0)))
                        #         if len(matches) >= batch_size:
                        #             dbInsertMatches(conn, matches)
                        #             matches.clear()
            except UnicodeDecodeError as e:
                errors.append((file_path, f"Unicode decode error: {str(e)}"))
    except Exception as e:
        errors.append((file_path, f"General error: {str(e)}"))
    
    # Insert remaining matches and errors
    if matches:
        dbInsertMatches(conn, matches)
    if errors:
        dbInsertErrors(conn, errors)




def batchIterator(iterable, batch_size):
    it = iter(iterable)
    while batch := list(islice(it, batch_size)):
        yield batch

def searchDirectory(directory, patterns, cpp_patterns, conn):
    file_paths = [
        os.path.join(root, file)
        for root, _, files in os.walk(directory)
        for file in files
    ]

    print(f"Number of files to be scanned: {len(file_paths)}")

    # Process files in batches
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
