import os
import re
import mmap
import time
from queue import Queue
from threading import Thread
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from tqdm import tqdm
from itertools import islice

from dbInit import initDatabase
from dbOperations import dbInsertMatches, dbInsertErrors, markFileProcessed, getProcessedFiles
from patterns_Secrets import secretsPatterns
from patterns_UnsafeFunctions import cppPatterns

# Precompile patterns
compiled_patterns = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in secretsPatterns
]
compiled_cpp_patterns = [re.compile(p) for p in cppPatterns]

# Adjust batch size based on hardware
batch_size = max(1500, os.cpu_count() * 500)

def dbWorker(queue, db_path):
    conn = initDatabase(db_path)  # Open a new connection for this thread
    while True:
        item = queue.get()
        if item is None:  # Exit signal
            break
        operation, data = item
        try:
            if operation == "matches":
                dbInsertMatches(conn, data)
            elif operation == "errors":
                dbInsertErrors(conn, data)
            elif operation == "processed":
                markFileProcessed(conn, data)
        except Exception as e:
            print(f"Database error during '{operation}' operation: {e}")
        queue.task_done()
    conn.close()

def searchFile(file_path, patterns, cpp_patterns, db_queue, batch_size=100):
    matches = []
    errors = []

    try:
        with open(file_path, 'rb') as file:
            try:
                with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                    content = mmapped_file.read().decode('utf-8', errors='ignore')  # Read full file content
                    for pattern in patterns:
                        for match in pattern.finditer(content):
                            matches.append((pattern.pattern, file_path, 0, match.group(0)))
                            if len(matches) >= batch_size:
                                db_queue.put(("matches", matches))
                                matches = []
            except UnicodeDecodeError as e:
                errors.append((file_path, f"Unicode decode error: {str(e)}"))
    except Exception as e:
        errors.append((file_path, f"General error: {str(e)}"))

    if matches:
        db_queue.put(("matches", matches))
    if errors:
        db_queue.put(("errors", errors))

    db_queue.put(("processed", file_path))

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

    db_queue = Queue()
    db_thread = Thread(target=dbWorker, args=(db_queue, db_path))
    db_thread.start()

    start_time = time.time()
    processed_count = 0

    with ThreadPoolExecutor() as executor:
        for batch in tqdm(batchIterator(file_paths, batch_size), total=len(file_paths) // batch_size, leave=False):
            partial_search = partial(
                searchFile,
                patterns=compiled_patterns,
                cpp_patterns=compiled_cpp_patterns,
                db_queue=db_queue,
                batch_size=batch_size,
            )
            for _ in executor.map(partial_search, batch):
                processed_count += 1
                if processed_count % 1000 == 0 or time.time() - start_time >= 5:
                    print(f"Processed {processed_count}/{len(file_paths)} files...")
                    start_time = time.time()

    db_queue.put(None)
    db_thread.join()

def main():
    directory = input("Enter the directory path to search: ").strip()
    if not os.path.isdir(directory):
        print(f"Error: The provided path is not a valid directory: {directory}")
        return
    db_path = "results.db"
    searchDirectory(directory, compiled_patterns, compiled_cpp_patterns, db_path)

if __name__ == '__main__':
    main()
