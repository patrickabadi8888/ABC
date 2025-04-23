import os
import re
import sys

def generate_files_from_string(input_text):
    # Pattern: a path line, then a ```java block with code until ```
    file_pattern = re.compile(r"(?m)^(?P<path>[\w/\\.]+\.java)\s*```java\s*(?P<code>.*?)```", re.DOTALL)
    for match in file_pattern.finditer(input_text):
        file_path = match.group('path').strip()
        code = match.group('code').rstrip() + '\n'
        # Create directories
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            print(f"Created directory: {dir_name}")
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"Written file: {file_path}")

if __name__ == '__main__':
    input_file = 'H.txt'
    with open(input_file, 'r', encoding='utf-8') as f:
        input_text = f.read()
    generate_files_from_string(input_text)
    print("All files generated.")
