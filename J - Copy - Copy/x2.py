import os

def find_java_files_with_contents(start_directory):
    """Find all Java files, count their lines, and read their contents."""
    files_info = []
    for root, _, files in os.walk(start_directory):
        for fname in files:
            if not('Controllers' in root or 'Services' in root or 'Views' in root or 'BTOApp.java' in fname):
                continue
            if fname.endswith('.java'):
                path = os.path.join(root, fname)
                rel = os.path.relpath(path, start_directory)
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    contents = f.read()
                # count lines in a robust way
                line_count = len(contents.splitlines())
                class_count = contents.count('class ')
                files_info.append((rel, line_count, class_count, contents))
    return files_info

def write_summary(files_info, output_path):
    """Write the summary report to the given output file."""
    # sort descending by line count
    files_info.sort(key=lambda x: x[1], reverse=True)
    
    with open(output_path, 'w', encoding='utf-8') as out:
        for rel_path, count, class_count, contents in files_info:
            out.write(f"{rel_path} ({count})\n")
            print(f"{rel_path} ({count}) {class_count})")
            out.write("```java\n")
            out.write(contents)
            # ensure there's a trailing newline before closing the fence
            if not contents.endswith('\n'):
                out.write('\n')
            out.write("```\n\n")

if __name__ == '__main__':
    start_dir = '.'
    output_file = '.s.txt'
    
    data = find_java_files_with_contents(start_dir)
    write_summary(data, output_file)
    print(f"Report written to {output_file}")
    print("Total files found:", len(data))