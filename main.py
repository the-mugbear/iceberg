import os
import re
import mmap
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
compiled_patterns = [re.compile(p) for p in secretsPatterns]
compiled_cpp_patterns = [re.compile(p) for p in cppPatterns]

# Adjust batch size based on hardware
batch_size = max(1500, os.cpu_count() * 500)

def dbWorker(queue, db_path):
    """
    Worker function to handle database operations from the queue.
    """
    conn = initDatabase(db_path)  # Open a new connection for this thread
    while True:
        item = queue.get()
        if item is None:  # Exit signal
            break

        operation, data = item
        if operation == "matches":
            dbInsertMatches(conn, data)
        elif operation == "errors":
            dbInsertErrors(conn, data)
        elif operation == "processed":
            markFileProcessed(conn, data)
        queue.task_done()
    conn.close()

def searchFile(file_path, patterns, cpp_patterns, db_queue, batch_size=100):
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
                                    db_queue.put(("matches", matches))
                                    matches = []

                        # Uncomment to enable unsafe function detection
                        # for cpp_pattern in cpp_patterns:
                        #     if match := cpp_pattern.search(line):
                        #         matches.append((cpp_pattern.pattern, file_path, line_number, match.group(0)))
                        #         if len(matches) >= batch_size:
                        #             db_queue.put(("matches", matches))
                        #             matches = []
            except UnicodeDecodeError as e:
                errors.append((file_path, f"Unicode decode error: {str(e)}"))
    except Exception as e:
        errors.append((file_path, f"General error: {str(e)}"))

    # Add remaining matches and errors to the queue
    if matches:
        db_queue.put(("matches", matches))
    if errors:
        db_queue.put(("errors", errors))

    # Mark file as processed
    db_queue.put(("processed", file_path))

def batchIterator(iterable, batch_size):
    it = iter(iterable)
    while batch := list(islice(it, batch_size)):
        yield batch

def searchDirectory(directory, patterns, cpp_patterns, db_path):
    # Fetch already processed files
    conn = initDatabase(db_path)
    processed_files = getProcessedFiles(conn)
    conn.close()

    file_paths = [
        os.path.join(root, file)
        for root, _, files in os.walk(directory)
        for file in files
        if os.path.join(root, file) not in processed_files  # Skip processed files
    ]

    print(f"Number of files to be scanned: {len(file_paths)}")

    # Initialize database queue and worker thread
    db_queue = Queue()
    db_thread = Thread(target=dbWorker, args=(db_queue, db_path))
    db_thread.start()

    # Process files in batches
    with ThreadPoolExecutor() as executor:
        for batch in tqdm(batchIterator(file_paths, batch_size), total=len(file_paths) // batch_size, mininterval=1.0):
            partial_search = partial(
                searchFile,
                patterns=compiled_patterns,
                cpp_patterns=compiled_cpp_patterns,
                db_queue=db_queue,
                batch_size=batch_size,
            )
            executor.map(partial_search, batch)

    # Signal the worker thread to stop and wait for it to finish
    db_queue.put(None)
    db_thread.join()

def main():
    directory = input("Enter the directory path to search: ").strip()
    if not os.path.isdir(directory):
        print(f"Error: The provided path is not a valid directory: {directory}")
        return

    db_path = "results.db"  # Path to the SQLite database
    searchDirectory(directory, compiled_patterns, compiled_cpp_patterns, db_path)

if __name__ == '__main__':
    main()
