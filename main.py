import os
import re
import mmap
import time
import math
from queue import Queue
from threading import Thread, Lock
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from tqdm import tqdm
from itertools import islice

from dbInit import initDatabase
from dbOperations import dbInsertMatches, dbInsertErrors, markFileProcessed, getProcessedFiles
from patterns_Secrets import secretsPatterns
from patterns_UnsafeFunctions import cppPatterns

# Precompile regex patterns for better performance
# ----------------------------------------------
# MULTILINE flag: ^ and $ match start/end of each line
# DOTALL flag: . matches newline characters
# IGNORECASE flag: case-insensitive matching
# TODO: Evaluation of compiled vs not compiled so far negligible 
compiled_patterns = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in secretsPatterns
]
compiled_cpp_patterns = [re.compile(p) for p in cppPatterns]

# Adjust batch size based on hardware
batch_size = max(1500, os.cpu_count() * 500)

# Thread-safe counter
processed_count = 0
processed_count_lock = Lock()

def dbWorker(queue, db_path):
    """
    Database worker thread that processes database operations from a queue.
    
    Threading Implementation:
    - Each dbWorker runs in its own thread
    - Multiple dbWorkers (up to 4) run concurrently to handle database operations
    - Each worker has its own database connection to prevent threading issues
    
    Queue Operations:
    - Workers process items from the queue until they receive None (shutdown signal)
    - Queue items are tuples of (operation, data) where operation is one of:
        * "matches": Insert pattern matches
        * "errors": Insert error records
        * "processed": Mark file as processed
    
    Args:
        queue (Queue): Thread-safe queue containing database operations
        db_path (str): Path to the SQLite database file
    """
    conn = initDatabase(db_path)  # Each thread gets its own connection
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

    # Update processed count in a thread-safe manner
    global processed_count
    with processed_count_lock:
        processed_count += 1

def batchIterator(iterable, batch_size):
    """
    Creates batches of items from an iterable for efficient processing.
    
    Batching Strategy:
    - Takes an iterable (like a list of file paths) and yields fixed-size batches
    - Uses islice for memory-efficient iteration without creating intermediate lists
    - Last batch may be smaller than batch_size
    
    Example:
        Files: [f1, f2, f3, f4, f5] with batch_size=2
        Yields: [f1, f2], [f3, f4], [f5]
    
    Args:
        iterable: Input iterable to be batched
        batch_size: Number of items per batch
    
    Yields:
        Lists of items of size batch_size (or smaller for the last batch)
    """
    it = iter(iterable)
    while batch := list(islice(it, batch_size)):
        yield batch

def searchDirectory(directory, patterns, cpp_patterns, db_path):
    """
    Main function that coordinates multi-threaded file scanning and database operations.
    
    Threading Architecture:
    1. Database Workers:
        - Multiple db_queues (up to 4) to distribute database operations
        - Each queue has its own dbWorker thread
        - Files are assigned to queues using hash(file_path) for even distribution
    
    2. File Processing Workers:
        - ThreadPoolExecutor manages a pool of worker threads
        - Number of workers = CPU_COUNT
        - Each worker processes one file at a time
        - Files are processed in batches for better efficiency
    
    Batch Processing Flow:
    1. Files are gathered and filtered (by extension and already processed)
    2. Files are divided into batches using batchIterator
    3. Each batch is submitted to the ThreadPoolExecutor
    4. Completed files are tracked using as_completed()
    
    Progress Monitoring:
    - Tracks processed files and calculates processing rate
    - Estimates time remaining based on current processing speed
    """
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

    # Initialize database worker threads and queues
    db_queue = Queue()
    db_thread = Thread(target=dbWorker, args=(db_queue, db_path))
    db_thread.start()

    start_time = time.time()

    # Process files using thread pool
    with ThreadPoolExecutor() as executor:
        total_batches = math.ceil(len(file_paths) / batch_size)
        for batch in tqdm(batchIterator(file_paths, batch_size), total=total_batches, leave=False):
            partial_search = partial(
                searchFile,
                patterns=compiled_patterns,
                cpp_patterns=compiled_cpp_patterns,
                db_queue=db_queue,
                batch_size=batch_size,
            )
            list(executor.map(partial_search, batch))  # Ensure all tasks are processed

            # Print progress every 1000 files or 5 seconds
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