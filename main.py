import os
import re
import time
import tempfile
from queue import Queue
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice

from dbInit import initDatabase
from dbOperations import dbInsertMatches, dbInsertErrors, markFileProcessed, getProcessedFiles
from patterns_Secrets import secretsPatterns
from patterns_UnsafeFunctions import cppPatterns

# Precompile regex patterns for better performance
compiled_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in secretsPatterns]
compiled_cpp_patterns = [re.compile(p) for p in cppPatterns]

# Adjust batch size based on hardware
batch_size = max(1500, os.cpu_count() * 500)

# Thread-safe counter
processed_count = 0
processed_count_lock = Lock()

def searchFile(file_path, patterns, cpp_patterns, temp_file):
    global processed_count
    errors = []

    try:
        with open(file_path, 'rb') as file:
            content = file.read().decode('utf-8', errors='ignore')  # Read full file content once
            for pattern in patterns:
                for match in pattern.finditer(content):
                    temp_file.write(f"{pattern.pattern}\t{file_path}\t0\t{match.group(0)}\n")
    except Exception as e:
        errors.append((file_path, f"General error: {str(e)}"))

    if errors:
        with processed_count_lock:
            temp_file.write('\n'.join([f"ERROR\t{file_path}\t{msg}" for file_path, msg in errors]) + '\n')

    # Update processed count in a thread-safe manner
    with processed_count_lock:
        processed_count += 1
        if processed_count % 1000 == 0:
            print(f"Processed {processed_count} files...")

def batchIterator(iterable, batch_size):
    it = iter(iterable)
    while batch := list(islice(it, batch_size)):
        yield batch

def searchDirectory(directory, patterns, cpp_patterns, db_path):
    conn = initDatabase(db_path)
    processed_files = getProcessedFiles(conn)
    conn.close()

    file_paths = [
        os.path.join(root, file)
        for root, _, files in os.walk(directory)
        for file in files
        if os.path.join(root, file) not in processed_files
    ]

    print(f"Number of files to be scanned: {len(file_paths)}")

    # Initialize temporary file for matches
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file_path = temp_file.name

        # Process files using thread pool
        with ThreadPoolExecutor() as executor:
            futures = []
            for batch in batchIterator(file_paths, batch_size):
                futures.extend(executor.submit(searchFile, file, patterns, cpp_patterns, temp_file) for file in batch)

            for future in as_completed(futures):
                future.result()  # Ensure all tasks are processed

        # Process temporary file into the database
        conn = initDatabase(db_path)
        matches = []
        errors = []
        with open(temp_file_path, 'r') as temp_file:
            for line in temp_file:
                if line.startswith("ERROR"):
                    _, file_path, msg = line.strip().split('\t')
                    errors.append((file_path, msg))
                else:
                    pattern, file_path, _, match = line.strip().split('\t')
                    matches.append((pattern, file_path, 0, match))
                    if len(matches) >= batch_size:
                        dbInsertMatches(conn, matches)
                        matches = []
            if matches:
                dbInsertMatches(conn, matches)
            if errors:
                dbInsertErrors(conn, errors)
        conn.close()

        os.remove(temp_file_path)

def main():
    directory = input("Enter the directory path to search: ").strip()
    if not os.path.isdir(directory):
        print(f"Error: The provided path is not a valid directory: {directory}")
        return
    db_path = "results.db"
    searchDirectory(directory, compiled_patterns, compiled_cpp_patterns, db_path)

if __name__ == '__main__':
    main()