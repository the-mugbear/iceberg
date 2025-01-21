import os
import re
import mmap
import time
import math
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from itertools import islice

from dbInit import initDatabase
from dbOperations import dbInsertMatches, dbInsertErrors, markFileProcessed, getProcessedFiles
from patterns_Secrets import secretsPatterns
from patterns_UnsafeFunctions import cppPatterns

# ========== Configuration ==========
TEMP_MATCHES_FILE = "matches_temp.txt"
TEMP_ERRORS_FILE = "errors_temp.txt"
PROCESSED_FILES_BATCH_SIZE = 1000
BATCH_SIZE = max(1500, os.cpu_count() * 500)  # For file processing
# ===================================

# Thread-safe locks for writing to temp files
matches_lock = threading.Lock()
errors_lock = threading.Lock()

# Thread-safe counter for progress
processed_count = 0
processed_count_lock = threading.Lock()

# Precompile regex patterns
compiled_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in secretsPatterns]
compiled_cpp_patterns = [re.compile(p) for p in cppPatterns]

def write_matches_to_file(matches):
    """
    Appends matches to a shared text file in a thread-safe manner.
    Each match is written as a CSV-like line.
    """
    with matches_lock:
        with open(TEMP_MATCHES_FILE, "a", encoding="utf-8") as f:
            for m in matches:
                pattern, file_path, line_number, content = m
                # Escape or quote if needed, here we keep it simple
                f.write(f"{pattern}|{file_path}|{line_number}|{content}\n")

def write_errors_to_file(errors):
    """
    Appends errors to a shared text file in a thread-safe manner.
    Each error is written as file_path|error_message.
    """
    with errors_lock:
        with open(TEMP_ERRORS_FILE, "a", encoding="utf-8") as f:
            for e in errors:
                file_path, error_msg = e
                f.write(f"{file_path}|{error_msg}\n")

def search_file(file_path, patterns, cpp_patterns):
    """
    Scans a single file for matches, writes them to temp files, and notes errors if any.
    """
    matches = []
    errors = []

    try:
        with open(file_path, 'rb') as file:
            with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                content = mmapped_file.read().decode('utf-8', errors='ignore')
                # Process secret patterns
                for pattern in patterns:
                    for match in pattern.finditer(content):
                        matches.append((pattern.pattern, file_path, 0, match.group(0)))
                # (Optional) process unsafe C++ patterns
                for cpp_pattern in cpp_patterns:
                    for match in cpp_pattern.finditer(content):
                        matches.append((cpp_pattern.pattern, file_path, 0, match.group(0)))
    except UnicodeDecodeError as e:
        errors.append((file_path, f"Unicode decode error: {str(e)}"))
    except Exception as e:
        errors.append((file_path, f"General error: {str(e)}"))

    # Write results to temp files
    if matches:
        write_matches_to_file(matches)
    if errors:
        write_errors_to_file(errors)

    # Thread-safe increment of processed file count
    global processed_count
    with processed_count_lock:
        processed_count += 1

def batch_iterator(iterable, batch_size):
    """
    Yields lists of size batch_size from iterable until exhausted.
    """
    it = iter(iterable)
    while True:
        batch = list(islice(it, batch_size))
        if not batch:
            break
        yield batch

def load_matches_into_db(db_path):
    """
    Loads match records from TEMP_MATCHES_FILE into the database in big chunks,
    then does the same for errors in TEMP_ERRORS_FILE.
    """
    conn = initDatabase(db_path)

    # Bulk insert matches
    try:
        with open(TEMP_MATCHES_FILE, "r", encoding="utf-8") as f:
            batch = []
            for line in f:
                line = line.rstrip("\n")
                pattern, file_path, line_number, content = line.split("|", 3)
                batch.append((pattern, file_path, line_number, content))
                if len(batch) >= 1000:
                    dbInsertMatches(conn, batch)
                    batch.clear()
            # Insert any remaining
            if batch:
                dbInsertMatches(conn, batch)
    except FileNotFoundError:
        print("No matches_temp.txt found, skipping match insertion.")
    except Exception as e:
        print(f"Error inserting matches: {e}")

    # Bulk insert errors
    try:
        with open(TEMP_ERRORS_FILE, "r", encoding="utf-8") as f:
            batch = []
            for line in f:
                line = line.rstrip("\n")
                file_path, error_msg = line.split("|", 1)
                batch.append((file_path, error_msg))
                if len(batch) >= 1000:
                    dbInsertErrors(conn, batch)
                    batch.clear()
            # Insert remainder
            if batch:
                dbInsertErrors(conn, batch)
    except FileNotFoundError:
        print("No errors_temp.txt found, skipping error insertion.")
    except Exception as e:
        print(f"Error inserting errors: {e}")

    conn.close()

def mark_files_processed(db_path, processed_files):
    """
    Marks processed files in larger batches to reduce DB overhead.
    """
    conn = initDatabase(db_path)
    batch = []
    for file_path in processed_files:
        batch.append(file_path)
        if len(batch) >= PROCESSED_FILES_BATCH_SIZE:
            for fp in batch:
                markFileProcessed(conn, fp)
            batch.clear()
    if batch:
        for fp in batch:
            markFileProcessed(conn, fp)
    conn.close()

def search_directory(directory, patterns, cpp_patterns, db_path):
    """
    Main scanning function. Gathers file paths, excludes already processed,
    spawns threads to scan them, writes results to temp files,
    then does a final bulk insert.
    """
    # Prep: remove old temp files
    for temp_file in [TEMP_MATCHES_FILE, TEMP_ERRORS_FILE]:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    # Identify files not yet processed
    conn = initDatabase(db_path)
    processed_db = getProcessedFiles(conn)  # set of processed paths
    conn.close()

    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            if full_path not in processed_db:
                file_paths.append(full_path)

    print(f"Number of files to be scanned: {len(file_paths)}")

    # Scan files in parallel
    start_time = time.time()
    with ThreadPoolExecutor() as executor:
        total_batches = math.ceil(len(file_paths) / BATCH_SIZE)
        for batch in batch_iterator(file_paths, BATCH_SIZE):
            partial_search = partial(
                search_file,
                patterns=patterns,
                cpp_patterns=cpp_patterns
            )
            # Wait for all tasks in this batch
            list(executor.map(partial_search, batch))

            # Print progress every 5 seconds or so
            if (processed_count % 1000 == 0) or (time.time() - start_time >= 5):
                print(f"Processed {processed_count}/{len(file_paths)} files...")
                start_time = time.time()

    # Mark all files as processed in the DB
    mark_files_processed(db_path, file_paths)

    # Finally bulk-insert from temp files to DB
    load_matches_into_db(db_path)

def main():
    directory = input("Enter the directory path to search: ").strip()
    if not os.path.isdir(directory):
        print(f"Error: The provided path is not a valid directory: {directory}")
        return

    db_path = "results.db"

    search_directory(directory, compiled_patterns, compiled_cpp_patterns, db_path)

    print("Scan complete.")

if __name__ == '__main__':
    main()
