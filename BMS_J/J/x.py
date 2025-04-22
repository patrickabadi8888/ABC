# Print all java in current folder and subfolder, with number of lines in the code in brackets beside, with the lines to show is subfolder
import os
import re

def count_lines_of_code(file_path):
    """Count the number of lines of code in a file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        lines = file.readlines()
    return len(lines)

def find_java_files_with_line_count(start_directory):
    """Find all Java files in the given directory and its subdirectories, and print their paths with line counts."""
    java_files = []
    for root, dirs, files in os.walk(start_directory):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                line_count = count_lines_of_code(file_path)
                relative_path = os.path.relpath(file_path, start_directory)
                java_files.append((relative_path, line_count))
    return java_files

data = find_java_files_with_line_count('.')

# sorted by line count
data.sort(key=lambda x: x[1], reverse=True)

# print the result
for file_path, line_count in data:
    print(f"{file_path} ({line_count})")
