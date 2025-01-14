import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from functools import partial
from tqdm import tqdm
import mmap

# Define your patterns
patterns = [r'password\s*=\s*["\']([^"\']+)["\']', r'api[_-]?key\s*=\s*["\']([^"\']+)["\']']
cpp_patterns = [r'\bstrcpy\s*\(', r'\bmalloc\s*\(', r'\bsystem\s*\(']

# Precompile patterns
compiled_patterns = [re.compile(p) for p in patterns]
compiled_cpp_patterns = [re.compile(p) for p in cpp_patterns]

# Allowed file extensions for filtering
ALLOWED_EXTENSIONS = {".txt", ".cpp", ".py", ".log"}


def write_match(pattern_name, match_line, file_path, line_number, output_dir, subfolder, metrics):
    """
    Writes a match to a file in a specific subfolder within the output directory.
    """
    subfolder_path = os.path.join(output_dir, subfolder)
    os.makedirs(subfolder_path, exist_ok=True)
    sanitized_name = re.sub(r'[^\w\d]', '_', pattern_name)
    output_file_path = os.path.join(subfolder_path, f"{sanitized_name}.txt")

    with open(output_file_path, 'a', encoding='utf-8') as output_file:
        output_file.write(f"File: {file_path} | Line {line_number}: {match_line.strip()}\n")
    
    metrics[pattern_name] += 1


def write_aggregated_matches(aggregated_results, output_dir, subfolder):
    """
    Writes aggregated matches to a separate file in the specified subfolder.
    """
    aggregated_file_path = os.path.join(output_dir, subfolder, "aggregated_matches.txt")
    os.makedirs(os.path.join(output_dir, subfolder), exist_ok=True)

    with open(aggregated_file_path, 'w', encoding='utf-8') as aggregated_file:
        aggregated_file.write("=== Aggregated Matches ===\n")
        for file_path, matches in aggregated_results.items():
            aggregated_file.write(f"\nFile: {file_path}\n")
            for match in matches:
                aggregated_file.write(f"  Match: {match}\n")


def search_file(file_path, patterns, cpp_patterns, output_dir, metrics, aggregated_results):
    """
    Searches a single file for matches and categorizes results into subfolders.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                for line_number, line in enumerate(mmapped_file, start=1):
                    line = line.decode('utf-8', errors='ignore')
                    # Matches for patterns (secrets)
                    for pattern in patterns:
                        if pattern.search(line):
                            write_match(pattern.pattern, line, file_path, line_number, output_dir, "secrets", metrics)
                            aggregated_results[file_path].append(line.strip())
                    
                    # Matches for cpp_patterns (unsafe functions)
                    for cpp_pattern in cpp_patterns:
                        if cpp_pattern.search(line):
                            write_match(cpp_pattern.pattern, line, file_path, line_number, output_dir, "unsafe", metrics)
    except Exception as e:
        error_file = os.path.join(output_dir, "errors.txt")
        with open(error_file, 'a', encoding='utf-8') as error_log:
            error_log.write(f"Error reading file {file_path}: {e}\n")


def batch_iterator(iterable, batch_size):
    """
    Generates batches of files for processing.
    """
    it = iter(iterable)
    while batch := list(islice(it, batch_size)):
        yield batch


def search_directory(directory, patterns, cpp_patterns, output_dir, log_file):
    """
    Searches through a directory and organizes results into subfolders.
    """
    metrics = defaultdict(int)
    aggregated_results = defaultdict(list)
    file_paths = [
        os.path.join(root, file)
        for root, _, files in os.walk(directory)
        for file in files
        if os.path.splitext(file)[1].lower() in ALLOWED_EXTENSIONS
    ]
    log_file.write(f"Number of files to be scanned: {len(file_paths)}\n")

    # Process files in batches
    batch_size = 1000
    with ThreadPoolExecutor() as executor:
        for batch in tqdm(batch_iterator(file_paths, batch_size), total=len(file_paths) // batch_size):
            partial_search = partial(
                search_file,
                patterns=compiled_patterns,
                cpp_patterns=compiled_cpp_patterns,
                output_dir=output_dir,
                metrics=metrics,
                aggregated_results=aggregated_results,
            )
            executor.map(partial_search, batch)

    # Log metrics summary
    log_file.write("\n=== Metrics Summary ===\n")
    for pattern, count in metrics.items():
        log_file.write(f"{pattern}: {count} matches\n")

    # Write aggregated matches to separate subfolders
    write_aggregated_matches(aggregated_results, output_dir, "secrets")


def main():
    """
    Main entry point for the script.
    """
    directory = input("Enter the directory path to search: ").strip()
    if not os.path.isdir(directory):
        print(f"Error: The provided path is not a valid directory: {directory}")
        return

    output_dir = input("Enter the output directory path (e.g., output/): ").strip()
    if not output_dir:
        print("Error: Output directory path cannot be empty.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(output_dir, f"logfile_{timestamp}.txt")
    os.makedirs(output_dir, exist_ok=True)

    with open(log_filename, "a") as log_file:
        log_file.write(f"Scan started at {datetime.now()}\n")
        search_directory(directory, compiled_patterns, compiled_cpp_patterns, output_dir, log_file)
        log_file.write(f"Scan completed at {datetime.now()}\n")

if __name__ == '__main__':
    main()
