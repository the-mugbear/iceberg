import os

def extract_extensions(input_file):
    """
    Reads a .txt file, extracts filenames, and identifies unique file extensions.
    
    Args:
        input_file (str): Path to the input .txt file containing filenames.
    
    Returns:
        set: A set of unique file extensions.
    """
    extensions = set()  # To store unique extensions

    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            for line in file:
                filename = line.strip()
                _, ext = os.path.splitext(filename)
                if ext:  # Only add if the extension exists
                    extensions.add(ext.lower())  # Normalize to lowercase
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return extensions

def main():
    input_file = input("Enter the path to the .txt file containing filenames: ").strip()
    
    # Extract extensions
    extensions = extract_extensions(input_file)
    
    # Output results
    if extensions:
        print("\nUnique Extensions Found:")
        for ext in sorted(extensions):
            print(ext)
    else:
        print("\nNo valid extensions found in the file.")

if __name__ == "__main__":
    main()
