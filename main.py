import os
import re
from concurrent.futures import ProcessPoolExecutor
from patterns import patterns
from cpp_patterns import cpp_patterns

def write_match_to_file(pattern_name, match_line, file_path, line_number, output_dir):
    """
    Writes a match to a file named after the pattern in the output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    sanitized_name = re.sub(r'[^\w\d]', '_', pattern_name)
    output_file_path = os.path.join(output_dir, f"{sanitized_name}.txt")

    with open(output_file_path, 'a', encoding='utf-8') as output_file:
        output_file.write(f"File: {file_path} | Line {line_number}: {match_line.strip()}\n")

def search_in_file(file_path, patterns, cpp_patterns, output_dir):
    """
    Searches for patterns in a file and writes matches to files named after the patterns.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_number, line in enumerate(file, start=1):
                # Search for sensitive assignments
                for pattern in patterns:
                    if re.search(pattern, line):
                        write_match_to_file(pattern, line, file_path, line_number, output_dir)
                
                # Search for unsafe C++ functions
                for cpp_pattern in cpp_patterns:
                    if re.search(cpp_pattern, line):
                        write_match_to_file(cpp_pattern, line, file_path, line_number, output_dir)
    except Exception as e:
        error_file = os.path.join(output_dir, "errors.txt")
        with open(error_file, 'a', encoding='utf-8') as error_log:
            error_log.write(f"Error reading file {file_path}: {e}\n")

def process_file(file_path, patterns, cpp_patterns, output_dir):
    """
    Wrapper for search_in_file to use with parallel processing.
    """
    search_in_file(file_path, patterns, cpp_patterns, output_dir)

def search_directory_parallel(directory, patterns, cpp_patterns, output_dir):
    """
    Recursively searches through a directory using parallel processing.
    """
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_paths.append(os.path.join(root, file))
    
    # Use ProcessPoolExecutor for parallel processing
    with ProcessPoolExecutor() as executor:
        executor.map(process_file, file_paths, [patterns] * len(file_paths), [cpp_patterns] * len(file_paths), [output_dir] * len(file_paths))

def main():
    """
    Main function to take user input for directory and output directory path.
    """
    directory = input("Enter the directory path to search: ").strip()
    if not os.path.isdir(directory):
        print(f"Error: The provided path is not a valid directory: {directory}")
        return

    output_dir = input("Enter the output directory path (e.g., output/): ").strip()
    if not output_dir:
        print("Error: Output directory path cannot be empty.")
        return

    print(f"Starting parallel search in directory: {directory}")
    search_directory_parallel(directory, patterns, cpp_patterns, output_dir)
    print(f"Search complete. Results saved in {output_dir}")

if __name__ == '__main__':
    main()
