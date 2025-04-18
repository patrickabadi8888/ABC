import glob

# print all files and their contents in the format recursive
# # File name
#  File content
# ----
s = ''
for filename in glob.glob('*.py') + glob.glob('*/**/*.py'):
    if filename == "__init__.py":
        continue
    s += f'# File name: {filename}\n'
    
    with open(filename, 'r') as f:
        content = f.read()
        s += f'{content}\n'
    s += '----\n'

with open('all_files.txt', 'w') as f:
    f.write(s)