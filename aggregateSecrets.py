import os
import re

def parse_file(file_path):
    """
    Parses a file to extract entries matching the format:
    File: (filedirectory\filename) | Line (linecount): (match)
    
    Args:
        file_path (str): Path to the file to parse.
    
    Returns:
        list: A list of tuples with (filedirectory\filename, match).
    """
    results = []
    entry_pattern = re.compile(r'^File: (.+) \| Line \d+: (.+)$')  # Regex to match the entry format

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                match = entry_pattern.match(line.strip())
                if match:
                    results.append((match.group(1), match.group(2)))  # Extract filename and match
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    
    return results

def aggregate_folder(folder_path, output_file):
    """
    Parses all files in a folder and aggregates matching entries into a single output file.
    
    Args:
        folder_path (str): Path to the folder containing files to parse.
        output_file (str): Path to the output aggregate file.
    """
    aggregated_results = []

    try:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                entries = parse_file(file_path)
                aggregated_results.extend(entries)  # Collect all results
                
        # Write aggregated results to output file
        with open(output_file, 'w', encoding='utf-8') as output:
            for filepath, match in aggregated_results:
                output.write(f"{filepath},{match}\n")

        print(f"\nAggregated results written to {output_file}")
    except Exception as e:
        print(f"Error during aggregation: {e}")

def main():
    folder_path = input("Enter the folder path containing files to parse: ").strip()
    if not os.path.isdir(folder_path):
        print(f"Error: The provided path is not a valid directory: {folder_path}")
        return

    output_file = input("Enter the path for the aggregate output file (e.g., aggregate.csv): ").strip()
    if not output_file:
        print("Error: Output file path cannot be empty.")
        return

    aggregate_folder(folder_path, output_file)

if __name__ == "__main__":
    main()
