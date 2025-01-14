import os
import re
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from patterns import patterns
from cpp_patterns import cpp_patterns

def writeMatch(pattern_name, match_line, file_path, line_number, output_dir, subfolder, metrics):
    # Ensure the subfolder exists
    subfolder_path = os.path.join(output_dir, subfolder)
    os.makedirs(subfolder_path, exist_ok=True)

    # Sanitize the pattern name for use as a filename
    sanitized_name = re.sub(r'[^\w\d]', '_', pattern_name)
    output_file_path = os.path.join(subfolder_path, f"{sanitized_name}.txt")

    # Write the match to the file
    with open(output_file_path, 'a', encoding='utf-8') as output_file:
        output_file.write(f"File: {file_path} | Line {line_number}: {match_line.strip()}\n")
    
    # Update metrics
    if pattern_name not in metrics:
        metrics[pattern_name] = 0
    metrics[pattern_name] += 1



def write_aggregated_matches(aggregated_results, output_dir, subfolder):
    aggregated_file_path = os.path.join(output_dir, subfolder, "aggregated_matches.txt")
    os.makedirs(os.path.join(output_dir, subfolder), exist_ok=True)

    with open(aggregated_file_path, 'w', encoding='utf-8') as aggregated_file:
        aggregated_file.write("=== Aggregated Matches ===\n")
        for file_path, matches in aggregated_results.items():
            aggregated_file.write(f"\nFile: {file_path}\n")
            for match in matches:
                aggregated_file.write(f"  Match: {match}\n")



def searchFile(file_path, patterns, cpp_patterns, output_dir, metrics, aggregated_results):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_number, line in enumerate(file, start=1):
                # Matches for patterns (secrets)
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        writeMatch(pattern, line, file_path, line_number, output_dir, "secrets", metrics)
                        if file_path not in aggregated_results:
                            aggregated_results[file_path] = []
                        aggregated_results[file_path].append(line.strip())
                
                # Matches for cpp_patterns (unsafe functions)
                for cpp_pattern in cpp_patterns:
                    if re.search(cpp_pattern, line):
                        writeMatch(cpp_pattern, line, file_path, line_number, output_dir, "unsafe", metrics)
    except Exception as e:
        error_file = os.path.join(output_dir, "errors.txt")
        with open(error_file, 'a', encoding='utf-8') as error_log:
            error_log.write(f"Error reading file {file_path}: {e}\n")



def searchDirectory(directory, patterns, cpp_patterns, output_dir, log_file):
    metrics = {}
    aggregated_results = {}
    file_paths = [os.path.join(root, file) for root, _, files in os.walk(directory) for file in files]
    log_file.write(f"Number of files to be scanned: {len(file_paths)}\n")

    with ProcessPoolExecutor() as executor:
        partial_search = partial(
            searchFile,
            patterns=patterns,
            cpp_patterns=cpp_patterns,
            output_dir=output_dir,
            metrics=metrics,
            aggregated_results=aggregated_results
        )
        executor.map(partial_search, file_paths)

    # Log metrics summary
    log_file.write("\n=== Metrics Summary ===\n")
    for pattern, count in metrics.items():
        log_file.write(f"{pattern}: {count} matches\n")

    # Write aggregated matches to separate subfolders
    write_aggregated_matches(aggregated_results, output_dir, "secrets")



def main():
    directory = input("Enter the directory path to search: ").strip()
    if not os.path.isdir(directory):
        print(f"Error: The provided path is not a valid directory: {directory}")
        return

    output_dir = input("Enter the output directory path (e.g., output/): ").strip()
    if not output_dir:
        print("Error: Output directory path cannot be empty.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"logfile_{timestamp}.txt"

    with open(log_filename, "a") as log_file:
        log_file.write(f"Scan started at {datetime.now()}\n")
        searchDirectory(directory, patterns, cpp_patterns, output_dir, log_file)
        log_file.write(f"Scan completed at {datetime.now()}\n")

if __name__ == '__main__':
    main()
